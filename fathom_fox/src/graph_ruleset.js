import {element, out, rule, ruleset, score, type} from 'fathom-web';
import {isVisible } from "fathom-web/utilsForFrontend";

function tagName(fnode) {
  return fnode.element.tagName;
}

function elementType(fnode) {
  const type = fnode.element.type;
  if (type === undefined) {
    return "";
  }
  return type;
}

function autocompleteString(fnode) {
  const autocomplete = fnode.element.autocomplete;
  if (autocomplete === undefined) {
    return "";
  }
  return autocomplete;
}

function makeRuleset(coeffs, biases) {
  return ruleset([
      rule(element("*"), type("graph")),
      rule(type("graph"), score(tagName), {name: "tagName"}),
      rule(type("graph"), score(elementType), {name: "elementType"}),
      rule(type("graph"), score(isVisible), {name: "isVisible"}),
      rule(type("graph"), score(autocompleteString), {name: "autocompleteString"}),
      rule(type("graph"), out("graph")),
    ],
    coeffs,
    biases);
}

const trainees = new Map();

const VIEWPORT_SIZE = {
  width: 1366,
  height: 768,
};

const coefficients = [
  ["tagName", 1.0],
  ["elementType", 1.0],
  ["isVisible", 1.0],
  ["autocompleteString", 1.0]
]

const biases = [
  ["graph", 0.0],
]

const trainee = {
  viewportSize: VIEWPORT_SIZE,
  coeffs: new Map(coefficients),
  isTarget: fnode => {
    const type = fnode.element.type;
    if (type) {
      return type === 'password';
    }
    return false;
  },
  rulesetMaker: () => makeRuleset([
      ...coefficients],
    biases)
};
trainees.set("graph", trainee);

export default trainees;
