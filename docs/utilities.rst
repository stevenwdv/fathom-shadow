=================
Utility Functions
=================

In addition to components intrinsically tied to rulesets, Fathom comes with a variety of utility procedures for building scoring and other callback functions or just for improving the imperative shell around your ruleset.

Import them from ``fathom-web/utils``. For example...

   .. code-block:: js

      const {best} = require('fathom-web/utils');

.. autofunction:: attributesMatch
.. autofunction:: best
.. autofunction:: collapseWhitespace
.. autofunction:: domSort
.. autofunction:: first
.. autofunction:: getDefault
.. autofunction:: identity
.. autofunction:: inlineTextLength
.. autofunction:: inlineTexts
.. autofunction:: isBlock
.. autofunction:: isWhitespace
.. autofunction:: length
.. autofunction:: linkDensity
.. autofunction:: utils.max
   :short-name:
.. autofunction:: maxes
.. autofunction:: min
.. autoclass:: NiceSet
   :members:
.. autofunction:: numberOfMatches
.. autofunction:: page
.. autofunction:: reversed
.. autofunction:: rootElement
.. autofunction:: setDefault
.. autofunction:: sum
.. autofunction:: toposort
.. autofunction:: walk
