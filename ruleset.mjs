import {CycleError} from './exceptions';
import {Fnode} from './fnode';
import {getDefault, isDomElement, reversed, setDefault, toposort} from './utilsForFrontend';
import {out} from './rhs';
import {InwardRule, OutwardRule, rule} from './rule';


/**
 * Return a new :class:`Ruleset` containing the given rules.
 */
export function ruleset(rules, coeffs = [], biases = []) {
    return new Ruleset(rules, coeffs, biases);
}

/**
 * An unbound ruleset. Eventually, you'll be able to add rules to these. Then,
 * when you bind them by calling :func:`~Ruleset.against()`, the resulting
 * :class:`BoundRuleset` will be immutable.
 *
 * @arg rules {Array} :class:`Rule` instances
 * @arg coeffs {Map} A map of rule names to numerical weights, typically
 *     returned by the :doc:`optimizer<optimization>`.
 * @arg coeffsAndBiases {object} Optimized weights and biases of the neural net
 *      which lead to high accuracy and accurate confidence estimates. Example:
 *      ``{coeffs: [['someRuleName', 30.04], ...],
 *         biases: [['someType', 147.39], ...]}``.
 *
 *     This is all rolled into one argument so you can paste in a single blob
 *     of numbers from the optimizer. Coeffs all default to 1, biases to 0.
 */
class Ruleset {
    constructor(rules, coeffs = [], biases = []) {
        this._inRules = [];
        this._outRules = new Map();  // key -> rule
        this._rulesThatCouldEmit = new Map();  // type -> [rules]
        this._rulesThatCouldAdd = new Map();  // type -> [rules]
        // Private to the framework:
        this._coeffs = new Map(coeffs);  // rule name => coefficient
        this.biases = new Map(biases);  // type name => bias

        // Separate rules into out ones and in ones, and sock them away. We do
        // this here so mistakes raise errors early.
        for (let rule of rules) {
            if (rule instanceof InwardRule) {
                this._inRules.push(rule);

                // Keep track of what inward rules can emit or add:
                // TODO: Combine these hashes for space efficiency:
                const emittedTypes = rule.typesItCouldEmit();
                for (let type of emittedTypes) {
                    setDefault(this._rulesThatCouldEmit, type, () => []).push(rule);
                }
                for (let type of rule.typesItCouldAdd()) {
                    setDefault(this._rulesThatCouldAdd, type, () => []).push(rule);
                }
            } else if (rule instanceof OutwardRule) {
                this._outRules.set(rule.key(), rule);
            } else {
                throw new Error(`This element of ruleset()'s first param wasn't a rule: ${rule}`);
            }
        }
    }

    /**
     * Commit this ruleset to running against a specific DOM tree.
     *
     * This doesn't actually modify the Ruleset but rather returns a fresh
     * BoundRuleset, which contains caches and other stateful, per-DOM
     * bric-a-brac.
     */
    against(doc) {
        return new BoundRuleset(doc,
                                this._inRules,
                                this._outRules,
                                this._rulesThatCouldEmit,
                                this._rulesThatCouldAdd,
                                this._coeffs,
                                this.biases);
    }

    /**
     * Return all the rules (both inward and outward) that make up this ruleset.
     *
     * From this, you can construct another ruleset like this one but with your
     * own rules added.
     */
    rules() {
        return Array.from([...this._inRules, ...this._outRules.values()]);
    }
}

/**
 * A ruleset that is earmarked to analyze a certain DOM
 *
 * Carries a cache of rule results on that DOM. Typically comes from
 * :func:`Ruleset.against`.
 */
class BoundRuleset {
    /**
     * @arg inRules {Array} Non-out() rules
     * @arg outRules {Map} Output key -> out() rule
     */
    constructor(doc, inRules, outRules, rulesThatCouldEmit, rulesThatCouldAdd, coeffs, biases) {
        this.doc = doc;
        this._inRules = inRules;
        this._outRules = outRules;
        this._rulesThatCouldEmit = rulesThatCouldEmit;
        this._rulesThatCouldAdd = rulesThatCouldAdd;
        this._coeffs = coeffs;

        // Private, for the use of only helper classes:
        this.biases = biases;
        this._clearCaches();
        this.elementCache = new Map();  // DOM element => fnode about it
        this.doneRules = new Set();  // InwardRules that have been executed. OutwardRules can be executed more than once because they don't change any fnodes and are thus idempotent.
    }

    /**
     * Change my coefficients and biases after I've already been constructed.
     *
     * @arg coeffsAndBiases See the :class:`Ruleset` constructor.
     */
    setCoeffsAndBiases(coeffs, biases = []) {
        // Destructuring assignment doesn't make it through rollup properly
        // (https://github.com/rollup/rollup-plugin-commonjs/issues/358):
        this._coeffs = new Map(coeffs);
        this.biases = new Map(biases);
        this._clearCaches();
    }

    /**
     * Clear the typeCache and maxCache, usually in the wake of changing
     * ``this._coeffs``, because both of thise depend on weighted scores.
     */
    _clearCaches() {
        this.maxCache = new Map();  // type => Array of max fnode (or fnodes, if tied) of this type
        this.typeCache = new Map();  // type => Set of all fnodes of this type found so far. (The dependency resolution during execution ensures that individual types will be comprehensive just in time.)
    }

    /**
     * Return an array of zero or more fnodes.
     * @arg thing {string|Lhs|Node} Can be...
     *
     *       * A string which matches up with an "out" rule in the ruleset. If the
     *         out rule uses through(), the results of through's callback (which
     *         might not be fnodes) will be returned.
     *       * An arbitrary LHS which we calculate and return the results of
     *       * A DOM node, for which we will return the corresponding fnode
     *
     *     Results are cached in the first and third cases.
     */
    get(thing) {
        if (typeof thing === 'string') {
            if (this._outRules.has(thing)) {
                return Array.from(this._execute(this._outRules.get(thing)));
            } else {
                throw new Error(`There is no out() rule with key "${thing}".`);
            }
        } else if (isDomElement(thing)) {
            // Return the fnode and let it run type(foo) on demand, as people
            // ask it things like scoreFor(foo).
            return this.fnodeForElement(thing);
        } else if (thing.asLhs !== undefined) {
            // Make a temporary out rule, and run it. This may add things to
            // the ruleset's cache, but that's fine: it doesn't change any
            // future results; it just might make them faster. For example, if
            // you ask for .get(type('smoo')) twice, the second time will be a
            // cache hit.
            const outRule = rule(thing, out(Symbol('outKey')));
            return Array.from(this._execute(outRule));
        } else {
            throw new Error('ruleset.get() expects a string, an expression like on the left-hand side of a rule, or a DOM node.');
        }
    }

    /**
     * Return the weighted sum of the per-rule, per-type scores from a fnode.
     *
     * @arg mapOfScores a Map of rule name to the [0, 1] score it computed for
     *      the type in question
     */
    weightedScore(mapOfScores) {
        let total = 0;
        for (const [name, score] of mapOfScores) {
            total += score * getDefault(this._coeffs, name, () => 1);
        }
        return total;
    }

    // Provide an opaque context object to be made available to all ranker
    // functions.
    // context (object) {
    //     self.context = object;
    // }

    // -------- Methods below this point are private to the framework. --------

    /**
     * Return all the thus-far-unexecuted rules that will have to run to run
     * the requested rule, in the form of Map(prereq: [rulesItIsNeededBy]).
     */
    _prerequisitesTo(rule, undonePrereqs = new Map()) {
        for (let prereq of rule.prerequisites(this)) {
            if (!this.doneRules.has(prereq)) {
                // prereq is not already run. (If it were, we wouldn't care
                // about adding it to the graph.)
                const alreadyAdded = undonePrereqs.has(prereq);
                setDefault(undonePrereqs, prereq, () => []).push(rule);

                // alreadyAdded means we've already computed the prereqs of
                // this prereq and added them to undonePrereqs. So, now
                // that we've hooked up the rule to this prereq in the
                // graph, we can stop. But, if we haven't, then...
                if (!alreadyAdded) {
                    this._prerequisitesTo(prereq, undonePrereqs);
                }
            }
        }
        return undonePrereqs;
    }

    /**
     * Run the given rule (and its dependencies, in the proper order), and
     * return its results.
     *
     * The caller is responsible for ensuring that _execute() is not called
     * more than once for a given InwardRule, lest non-idempotent
     * transformations, like score contributions, be applied to fnodes more
     * than once.
     *
     * The basic idea is to sort rules in topological order (according to input
     * and output types) and then run them. On top of that, we do some
     * optimizations. We keep a cache of results by type (whether partial or
     * comprehensive--either way, the topology ensures that any
     * non-comprehensive typeCache entry is made comprehensive before another
     * rule needs it). And we prune our search for prerequisite rules at the
     * first encountered already-executed rule.
     */
    _execute(rule) {
        const prereqs = this._prerequisitesTo(rule);
        let sorted;
        try {
            sorted = [rule].concat(toposort(prereqs.keys(),
                                            prereq => prereqs.get(prereq)));
        } catch (exc) {
            if (exc instanceof CycleError) {
                throw new CycleError('There is a cyclic dependency in the ruleset.');
            } else {
                throw exc;
            }
        }
        let fnodes;
        for (let eachRule of reversed(sorted)) {
            // Sock each set of results away in this.typeCache:
            fnodes = eachRule.results(this);
        }
        return Array.from(fnodes);
    }

    /** @return {Rule[]} */
    inwardRulesThatCouldEmit(type) {
        return getDefault(this._rulesThatCouldEmit, type, () => []);
    }

    /** @return {Rule[]} */
    inwardRulesThatCouldAdd(type) {
        return getDefault(this._rulesThatCouldAdd, type, () => []);
    }

    /**
     * @return the Fathom node that describes the given DOM element. This does
     *     not trigger any execution, so the result may be incomplete.
     */
    fnodeForElement(element) {
        return setDefault(this.elementCache,
                          element,
                          () => new Fnode(element, this));
    }
}
