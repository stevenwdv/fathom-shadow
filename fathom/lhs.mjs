// The left-hand side of a rule

import {clusters, distance} from './clusters';
import {maxes, getDefault, max, NiceSet, setDefault, sum, min} from './utilsForFrontend';
import {querySelectorAllDeep} from 'query-selector-shadow-dom';


/**
 * Take nodes that match a given DOM selector. Example:
 * ``dom('meta[property="og:title"]')``
 *
 * Every ruleset has at least one ``dom`` or :func:`element` rule, as that is
 * where nodes begin to flow into the system. If run against a subtree of a
 * document, the root of the subtree is not considered as a possible match.
 */
export function dom(selector) {
    return new DomLhs(selector);
}

/**
 * Take a single given node if it matches a given DOM selector, without looking
 * through its descendents or ancestors. Otherwise, take no nodes. Example:
 * ``element('input')``
 *
 * This is useful for applications in which you want Fathom to classify an
 * element the user has selected, rather than scanning the whole page for
 * candidates.
 */
export function element(selector) {
    return new ElementLhs(selector);
}

/**
 * Rules and the LHSs and RHSs that comprise them have no mutable state. This
 * lets us make BoundRulesets from Rulesets without duplicating the rules. It
 * also lets us share a common cache among rules: multiple ones might care
 * about a cached type(), for instance; there isn't a one-to-one relationship
 * of storing with caring. There would also, because of the interdependencies
 * of rules in a ruleset, be little use in segmenting the caches: if you do
 * something that causes one to need to be cleared, you'll need to clear many
 * more as well.
 *
 * Lhses are responsible for maintaining ruleset.maxCache.
 *
 * Lhs and its subclasses are private to the Fathom framework.
 */
export class Lhs {
    constructor() {
        this._predicate = () => true;
    }

    /** Return a new Lhs of the appropriate kind, given its first call. */
    static fromFirstCall(firstCall) {
        // firstCall is never 'dom', because dom() directly returns a DomLhs.
        if (firstCall.method === 'type') {
            return new TypeLhs(...firstCall.args);
        } else if (firstCall.method === 'and') {
            return new AndLhs(firstCall.args);
        } else if (firstCall.method === 'nearest') {
            return new NearestLhs(firstCall.args);
        } else {
            throw new Error('The left-hand side of a rule() must start with dom(), type(), and(), or nearest().');
        }
    }

    /**
     * Prune nodes from consideration early in run execution, before scoring is
     * done.
     *
     * Reserve this for where you are sure it is always correct or when
     * performance demands it. It is generally preferable to use :func:`score`
     * and let the :doc:`trainer<training>` determine the relative significance
     * of each rule. Human intuition as to what is important is often wrong:
     * for example, one might assume that a music player website would include
     * the word "play", but this does not hold once you include sites in other
     * languages.
     *
     * Can be chained after :func:`type` or :func:`dom`.
     *
     * Example: ``dom('p').when(isVisible)``
     *
     * @arg {function} predicate Accepts a fnode and returns a boolean
     */
    when(predicate) {
        let lhs = this.clone();
        lhs._predicate = predicate;
        return lhs;
    }

    /**
     * Of all the dom nodes selected by type() or dom(), return only
     * the fnodes that satisfy all the predicates imposed by calls to
     * when()
     */
    fnodesSatisfyingWhen(fnodes) {
        return Array.from(fnodes).filter(this._predicate);
    }

    /**
     * Return an iterable of output fnodes selected by this left-hand-side
     * expression.
     *
     * Pre: The rules I depend on have already been run, and their results are
     * in ruleset.typeCache.
     *
     * @arg ruleset {BoundRuleset}
     */
    // fnodes (ruleset) {}

    /**
     * Check that a RHS-emitted fact is legal for this kind of LHS, and throw
     * an error if it isn't.
     */
    checkFact(fact) {}

    /**
     * Return the single type the output of the LHS is guaranteed to have.
     * Return undefined if there is no such single type we can ascertain.
     */
    guaranteedType() {}

    /**
     * Return the type I aggregate if I am an aggregate LHS; return undefined
     * otherwise.
     */
    aggregatedType() {}

    /**
     * Return each combination of types my selected nodes could be locally (that
     * is, by this rule only) constrained to have.
     *
     * For example, type(A) would return [A]. and(A, or(B, C)) would return
     * [AB, AC, ABC]. More examples:
     *
     * or(A, B) → typeIn(A, B, C)  # Finalizes A, B.   combos A, B, AB: finalizes AB. Optimization: there's no point in returning the last combo in ors. Compilation into 2 rules with identical RHSs will inherently implement this optimization.
     * or(A, B) → typeIn(A, B)  # Finalizes A, B
     * or(A, B) → A  # Finalizes B
     * and(A) -> A  # Finalizes nothing
     * and(A, B) -> A  # Finalizes nothing.   AB: Ø
     * and(A) -> typeIn(A, B)  # Finalizes A.   A
     * and(A, B) -> typeIn(A, B)  # Finalizes nothing.   AB
     * and(A, B) -> typeIn(A, B, C)  # Finalizes A, B.   AB
     * and(A, or(B, C)) -> D  # Finalizes A, B, C.   AB, AC, ABC: ABC
     * and(A, or(B, C)) -> B  # Finalizes A, C.   AB, AC, ABC: AC
     * type(A).not(and(A, B)) ->
     *
     * @return {NiceSet[]}
     */
    // possibleTypeCombinations() {}

    /**
     * Types mentioned in this LHS.
     *
     * In other words, the types I need to know the assignment status of before
     * I can make my selections
     *
     * @return NiceSet of strings
     */
    // typesMentioned() {}
}

class DomLhs extends Lhs {
    constructor(selector) {
        super();
        if (selector === undefined) {
            throw new Error('A querySelector()-style selector is required as the argument to ' + this._callName() + '().');
        }
        this.selector = selector;
    }

    /**
     * Return the name of this kind of LHS, for use in error messages.
     */
    _callName() {
        return 'dom';
    }

    clone() {
        return new this.constructor(this.selector);
    }

    fnodes(ruleset) {
        return this._domNodesToFilteredFnodes(
            ruleset,
            querySelectorAllDeep(this.selector, ruleset.doc));
    }

    /**
     * Turn a NodeList of DOM nodes into an array of fnodes, and filter out
     * those that don't match the :func:`when()` clause.
     */
    _domNodesToFilteredFnodes(ruleset, domNodes) {
        let ret = [];
        for (let i = 0; i < domNodes.length; i++) {
            ret.push(ruleset.fnodeForElement(domNodes[i]));
        }
        return this.fnodesSatisfyingWhen(ret);
    }

    checkFact(fact) {
        if (fact.type === undefined) {
            throw new Error(`The right-hand side of a ${this._callName()}() rule failed to specify a type. This means there is no way for its output to be used by later rules. All it specified was ${fact}.`);
        }
    }

    asLhs() {
        return this;
    }

    possibleTypeCombinations() {
        return [];
    }

    typesMentioned() {
        return new NiceSet();
    }
}

class ElementLhs extends DomLhs {
    _callName() {
        return 'element';
    }

    fnodes(ruleset) {
        return this._domNodesToFilteredFnodes(
            ruleset,
            ruleset.doc.matches(this.selector) ? [ruleset.doc] : []);
    }
}

/** Internal representation of a LHS constrained by type but not by max() */
class TypeLhs extends Lhs {
    constructor(type) {
        super();
        if (type === undefined) {
            throw new Error('A type name is required when calling type().');
        }
        this._type = type;  // the input type
    }

    clone() {
        return new this.constructor(this._type);
    }

    fnodes(ruleset) {
        const cached = getDefault(ruleset.typeCache, this._type, () => []);
        return this.fnodesSatisfyingWhen(cached);
    }

    /** Override the type previously specified by this constraint. */
    type(inputType) {
        // Preserve the class in case this is a TypeMaxLhs.
        return new this.constructor(inputType);
    }

    /**
     * Of the nodes selected by a ``type`` call to the left, constrain the LHS
     * to return only the max-scoring one. If there is a tie, more than 1 node
     * will be returned. Example: ``type('titley').max()``
     */
    max() {
        return new TypeMaxLhs(this._type);
    }

    /**
     * Take the nodes selected by a ``type`` call to the left, group them into
     * clusters, and return the nodes in the cluster that has the highest total
     * score (on the relevant type).
     *
     * Nodes come out in arbitrary order, so, if you plan to emit them,
     * consider using ``.out('whatever').allThrough(domSort)``. See
     * :func:`domSort`.
     *
     * If multiple clusters have equally high scores, return an arbitrary one,
     * because Fathom has no way to represent arrays of arrays in rulesets.
     *
     * @arg options {Object} The same depth costs taken by :func:`distance`,
     *     plus ``splittingDistance``, which is the distance beyond which 2
     *     clusters will be considered separate. ``splittingDistance``, if
     *     omitted, defaults to 3.
     */
    bestCluster(options) {
        return new BestClusterLhs(this._type, options);
    }

    // Other clustering calls could be called biggestCluster() (having the most
    // nodes) and bestAverageCluster() (having the highest average score).

    guaranteedType() {
        return this._type;
    }

    possibleTypeCombinations() {
        return [this.typesMentioned()];
    }

    typesMentioned() {
        return new NiceSet([this._type]);
    }
}

/**
 * Abstract LHS that is an aggregate function taken across all fnodes of a type
 *
 * The main point here is that any aggregate function over a (typed) set of
 * nodes depends on first computing all the rules that could emit those nodes
 * (nodes of that type).
 */
class AggregateTypeLhs extends TypeLhs {
    aggregatedType() {
        return this._type;
    }
}

/**
 * Internal representation of a LHS that has both type and max([NUMBER])
 * constraints. max(NUMBER != 1) support is not yet implemented.
 */
class TypeMaxLhs extends AggregateTypeLhs {
    /**
     * Return the max-scoring node (or nodes if there is a tie) of the given
     * type.
     */
    fnodes(ruleset) {
        // TODO: Optimize better. Walk the dependency tree, and run only the
        // rules that could possibly lead to a max result. As part of this,
        // make RHSs expose their max potential scores.
        const self = this;
        // Work around V8 bug:
        // https://stackoverflow.com/questions/32943776/using-super-within-an-
        // arrow-function-within-an-arrow-function-within-a-method
        const getSuperFnodes = () => super.fnodes(ruleset);
        return setDefault(
            ruleset.maxCache,
            this._type,
            function maxFnodesOfType() {
                return maxes(getSuperFnodes(), fnode => ruleset.weightedScore(fnode.scoresSoFarFor(self._type)));
            });
    }
}

class BestClusterLhs extends AggregateTypeLhs {
    constructor(type, options) {
        super(type);
        this._options = options || {splittingDistance: 3};
    }

    /**
     * Group the nodes of my type into clusters, and return the cluster with
     * the highest total score for that type.
     */
    fnodes(ruleset) {
        // Get the nodes of the type:
        const fnodesOfType = Array.from(super.fnodes(ruleset));
        if (fnodesOfType.length === 0) {
            return [];
        }
        // Cluster them:
        const clusts = clusters(
            fnodesOfType,
            this._options.splittingDistance,
            (a, b) => distance(a, b, this._options));
        // Tag each cluster with the total of its nodes' scores:
        const clustsAndSums = clusts.map(
            clust => [clust,
                      sum(clust.map(fnode => fnode.scoreFor(this._type)))]);
        // Return the highest-scoring cluster:
        return max(clustsAndSums, clustAndSum => clustAndSum[1])[0];
    }
}

class AndLhs extends Lhs {
    constructor(lhss) {
        super();

        // For the moment, we accept only type()s as args. TODO: Generalize to
        // type().max() and such later.
        this._args = lhss.map(sideToTypeLhs);
    }

    *fnodes(ruleset) {
        // Take an arbitrary one for starters. Optimization: we could always
        // choose the pickiest one to start with.
        const fnodes = this._args[0].fnodes(ruleset);
        // Then keep only the fnodes that have the type of every other arg:
        fnodeLoop: for (let fnode of fnodes) {
            for (let otherLhs of this._args.slice(1)) {
                // Optimization: could use a .hasTypeSoFar() below
                if (!fnode.hasType(otherLhs.guaranteedType())) {
                    // TODO: This is n^2. Why is there no set intersection in JS?!
                    continue fnodeLoop;
                }
            }
            yield fnode;
        }
    }

    possibleTypeCombinations() {
        return [this.typesMentioned()];
    }

    typesMentioned() {
        return new NiceSet(this._args.map(arg => arg.guaranteedType()));
    }
}

function sideToTypeLhs(side) {
    const lhs = side.asLhs();
    if (!(lhs.constructor === TypeLhs)) {
        throw new Error('and() and nearest() support only simple type() calls as arguments for now.');
        // TODO: Though we could solve this with a compilation step: and(type(A), type(B).max()) is equivalent to type(B).max() -> type(Bmax); and(type(A), type(Bmax)).
        // In fact, we should be able to compile most (any?) arbitrary and()s, including nested ands and and(type(...).max(), ...) constructions into several and(type(A), type(B), ...) rules.
    }
    return lhs;
}

class NearestLhs extends Lhs {
    constructor([a, b, distance]) {
        super();
        this._a = sideToTypeLhs(a);
        this._b = sideToTypeLhs(b);
        this._distance = distance;
    }

    /**
     * Return an iterable of {fnodes, transformer} pairs.
     */
    *fnodes(ruleset) {
        // Go through all the left arg's nodes. For each one, find the closest
        // right-arg's node. O(a * b). Once a right-arg's node is used, we
        // don't eliminate it from consideration, because then order of left-
        // args' nodes would matter.

        // TODO: Still not sure how to get the distance to factor into the
        // score unless we hard-code nearest() to do that. It's a
        // matter of not being able to bind on the RHS to the output of the
        // distance function on the LHS. Perhaps we could at least make
        // distance part of the note and read it in a props() callback.

        // We're assuming here that simple type() calls return just plain
        // fnodes, not {fnode, rhsTransformer} pairs:
        const as_ = this._a.fnodes(ruleset);
        const bs = Array.from(this._b.fnodes(ruleset));
        if (bs.length > 0) {
            // If bs is empty, there can be no nearest nodes, so don't emit any.
            for (const a of as_) {
                const nearest = min(bs, b => this._distance(a, b));
                yield {fnode: a,
                       rhsTransformer: function setNoteIfEmpty(fact) {
                           // If note is explicitly set by the RHS, let it take
                           // precedence, even though that makes this entire LHS
                           // pointless.
                           if (fact.note === undefined) {
                               fact.note = nearest;  // TODO: Wrap this in an object to make room to return distance later.
                           }
                           return fact;
                       }};
            }
        }
    }

    checkFact(fact) {
        // Barf if the fact doesn't set a type at least. It should be a *new* type or at least one that doesn't result in cycles, but we can't deduce that.
    }

    possibleTypeCombinations() {
        return [new NiceSet([this._a.guaranteedType()])];
    }

    typesMentioned() {
        return new NiceSet([this._a.guaranteedType(),
                            this._b.guaranteedType()]);
    }

    guaranteedType() {
        return this._a.guaranteedType();
    }
}
