import {Lhs} from './lhs';
import {InwardRhs} from './rhs';


export function props(callback) {
    return new Side({method: 'props', args: [callback]});
}

/** Constrain to an input type on the LHS, or apply a type on the RHS. */
export function type(theType) {
    return new Side({method: 'type', args: [theType]});
}

export function note(callback) {
    return new Side({method: 'note', args: [callback]});
}

export function score(scoreOrCallback) {
    return new Side({method: 'score', args: [scoreOrCallback]});
}

export function atMost(score) {
    return new Side({method: 'atMost', args: [score]});
}

export function typeIn(...types) {
    return new Side({method: 'typeIn', args: types});
}

export function conserveScore() {
    return new Side({method: 'conserveScore', args: []});
}

/**
 * Pull nodes that conform to multiple conditions at once.
 *
 * For example: ``and(type('title'), type('english'))``
 *
 * Caveats: ``and`` supports only simple ``type`` calls as arguments for now,
 * and it may fire off more rules as prerequisites than strictly necessary.
 * ``not`` and ``or`` don't exist yet, but you can express ``or`` the long way
 * around by having 2 rules with identical RHSs.
 */
export function and(...lhss) {
    return new Side({method: 'and', args: lhss});
}

/**
 * For each node ``a``, find the closest node ``b``, and attach it as a note on
 * the type specified by the RHS. If there are no nodes ``b``, do and emit
 * nothing.
 *
 * For example: ``nearest(type('image'), type('price'))``
 *
 * The score of the ``a`` can be multiplied into the new type's score by using
 * ``:method:InwardRhs#conserveScore``::
 *
 *     rule(nearest(type('image'), type('price')),
 *          type('imageWithPrice').score(2).conserveScore())
 *
 * Caveats: ``nearest`` supports only simple ``type`` calls as arguments for
 * now.
 */
export function nearest(a, b, distance = euclidean) {
    return new Side({method: 'nearest', args: [a, b, distance]});
}

/**
 * A chain of calls that can be compiled into a Rhs or Lhs, depending on its
 * position in a Rule. This lets us use type() as a leading call for both RHSs
 * and LHSs. I would prefer to do this dynamically, but that wouldn't compile
 * down to old versions of ES.
 */
class Side {
    constructor(...calls) {
        // A "call" is like {method: 'dom', args: ['p.smoo']}.
        this._calls = calls;
    }

    max() {
        return this._and('max');
    }

    bestCluster(options) {
        return this._and('bestCluster', options);
    }

    props(callback) {
        return this._and('props', callback);
    }

    type(...types) {
        return this._and('type', ...types);
    }

    note(callback) {
        return this._and('note', callback);
    }

    score(scoreOrCallback) {
        return this._and('score', scoreOrCallback);
    }

    atMost(score) {
        return this._and('atMost', score);
    }

    typeIn(...types) {
        return this._and('typeIn', ...types);
    }

    conserveScore() {
        return this._and('conserveScore');
    }

    and(...lhss) {
        return this._and('and', lhss);
    }

    _and(method, ...args) {
        return new this.constructor(...this._calls.concat({method, args}));
    }

    asLhs() {
        return this._asSide(Lhs.fromFirstCall(this._calls[0]), this._calls.slice(1));
    }

    asRhs() {
        return this._asSide(new InwardRhs(), this._calls);
    }

    _asSide(side, calls) {
        for (let call of calls) {
            side = side[call.method](...call.args);
        }
        return side;
    }

    when(pred) {
        return this._and('when', pred);
    }
}
