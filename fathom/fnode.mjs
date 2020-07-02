import {type} from './side';
import {getDefault, setDefault, sigmoid} from './utilsForFrontend';


/**
 * A wrapper around a DOM node, storing :term:`types<type>`,
 * :term:`scores<score>`, and :term:`notes<note>` that apply to it
 */
export class Fnode {
    /**
     * @arg element The DOM element described by the fnode.
     * @arg ruleset The ruleset which created the fnode.
     */
    constructor(element, ruleset) {
        if (element === undefined) {
            throw new Error("Someone tried to make a fnode without specifying the element they're talking about.");
        }
        /**
         * The raw DOM element this fnode describes
         */
        this.element = element;
        this._ruleset = ruleset;

        // A map of type => {score: number, note: anything}. `score` is always
        // present and defaults to 1. A note is set iff `note` is present and
        // not undefined.
        this._types = new Map();

        // Note: conserveScore() is temporarily absent in 3.0.
        //
        // By default, a fnode has an independent score for each of its types.
        // However, a RHS can opt to conserve the score of an upstream type,
        // carrying it forward into another type. To avoid runaway scores in
        // the case that multiple rules choose to do this, we limit the
        // contribution of an upstream type's score to being multiplied in a
        // single time. In this set, we keep track of which upstream types'
        // scores have already been multiplied into each type. LHS fnode => Set
        // of types whose score for that node have been multiplied into this
        // node's score.
        this._conservedScores = new Map();
    }

    /**
     * Return whether the given type is one of the ones attached to the fnode.
     */
    hasType(type) {
        // Run type(theType) against the ruleset to make sure this doesn't
        // return false just because we haven't lazily run certain rules yet.
        this._computeType(type);
        return this._types.has(type);
    }

    /**
     * Return the confidence, in the range (0, 1), that the fnode belongs to the
     * given type, 0 by default.
     */
    scoreFor(type) {
        this._computeType(type);
        return sigmoid(this._ruleset.weightedScore(this.scoresSoFarFor(type)) +
                       getDefault(this._ruleset.biases, type, () => 0));
    }

    /**
     * Return the fnode's note for the given type, ``undefined`` if none.
     */
    noteFor(type) {
        this._computeType(type);
        return this._noteSoFarFor(type);
    }

    /**
     * Return whether this fnode has a note for the given type.
     *
     * ``undefined`` is not considered a note and may be overwritten with
     * impunity.
     */
    hasNoteFor(type) {
        this._computeType(type);
        return this._hasNoteSoFarFor(type);
    }

    // -------- Methods below this point are private to the framework. --------

    /**
     * Return an iterable of the types tagged onto me by rules that have
     * already executed.
     */
    typesSoFar() {
        return this._types.keys();
    }

    _noteSoFarFor(type) {
        return this._typeRecordForGetting(type).note;
    }

    _hasNoteSoFarFor(type) {
        return this._noteSoFarFor(type) !== undefined;
    }

    /**
     * Return the score thus far computed on me for a certain type. Doesn't
     * implicitly run any rules. If no score has yet been determined for the
     * given type, return undefined.
     */
    scoresSoFarFor(type) {
        return this._typeRecordForGetting(type).score;
    }

    /**
     * Add a given number to one of our per-type scores. Implicitly assign us
     * the given type. Keep track of which rule it resulted from so we can
     * later mess with the coeffs.
     */
    addScoreFor(type, score, ruleName) {
        this._typeRecordForSetting(type).score.set(ruleName, score);
    }

    /**
     * Set the note attached to one of our types. Implicitly assign us that
     * type if we don't have it already.
     */
    setNoteFor(type, note) {
        if (this._hasNoteSoFarFor(type)) {
            if (note !== undefined) {
                throw new Error(`Someone (likely the right-hand side of a rule) tried to add a note of type ${type} to an element, but one of that type already exists. Overwriting notes is not allowed, since it would make the order of rules matter.`);
            }
            // else the incoming note is undefined and we already have the
            // type, so it's a no-op
        } else {
            // Apply either a type and note or just a type (which means a note
            // that is undefined):
            this._typeRecordForSetting(type).note = note;
        }
    }

    /**
     * Return a score/note record for a type, creating it if it doesn't exist.
     */
    _typeRecordForSetting(type) {
        return setDefault(this._types, type, () => ({score: new Map()}));
    }

    /**
     * Manifest a temporary type record for reading, working around the lack of
     * a .? operator in JS.
     */
    _typeRecordForGetting(type) {
        return getDefault(this._types, type, () => ({score: new Map()}));
    }

    /**
     * Make sure any scores, notes, and type-tagging for the given type are
     * computed for my element.
     */
    _computeType(theType) {
        if (!this._types.has(theType)) {  // Prevent infinite recursion when an A->A rule looks at A's note in a callback.
            this._ruleset.get(type(theType));
        }
    }
}
