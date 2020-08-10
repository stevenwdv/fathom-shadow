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
  return getAutocompleteInfo(fnode.element).fieldName;
}

const AUTOFILL_FIELD_NAMES_MAX_TOKENS_AND_CATEGORY = {
  "off": [1, "Off"],
  "on": [1,"Automatic"],
  "name": [3,"Normal"],
  "honorific-prefix": [3,"Normal"],
  "given-name": [3,"Normal"],
  "additional-name": [3,"Normal"],
  "family-name": [3,"Normal"],
  "honorific-suffix": [3,"Normal"],
  "nickname": [3,"Normal"],
  "organization-title": [3,"Normal"],
  "username": [3,"Normal"],
  "new-password": [3,"Normal"],
  "current-password": [3,"Normal"],
  "one-time-code": [3,"Normal"],
  "organization": [3,"Normal"],
  "street-address": [3,"Normal"],
  "address-line1": [3,"Normal"],
  "address-line2": [3,"Normal"],
  "address-line3": [3,"Normal"],
  "address-level4": [3,"Normal"],
  "address-level3": [3,"Normal"],
  "address-level2": [3,"Normal"],
  "address-level1": [3,"Normal"],
  "country": [3,"Normal"],
  "country-name": [3,"Normal"],
  "postal-code": [3,"Normal"],
  "cc-name": [3,"Normal"],
  "cc-given-name": [3,"Normal"],
  "cc-additional-name": [3,"Normal"],
  "cc-family-name": [3,"Normal"],
  "cc-number": [3,"Normal"],
  "cc-exp": [3,"Normal"],
  "cc-exp-month": [3,"Normal"],
  "cc-exp-year": [3,"Normal"],
  "cc-csc": [3,"Normal"],
  "cc-type": [3,"Normal"],
  "transaction-currency": [3,"Normal"],
  "transaction-amount": [3,"Normal"],
  "language": [3,"Normal"],
  "bday": [3,"Normal"],
  "bday-day": [3,"Normal"],
  "bday-month": [3,"Normal"],
  "bday-year": [3,"Normal"],
  "sex": [3,"Normal"],
  "url": [3,"Normal"],
  "photo": [3,"Normal"],
  "tel": [4,"Contact"],
  "tel-country-code": [4,"Contact"],
  "tel-national": [4,"Contact"],
  "tel-area-code": [4,"Contact"],
  "tel-local": [4,"Contact"],
  "tel-local-prefix": [4,"Contact"],
  "tel-local-suffix": [4,"Contact"],
  "tel-extension": [4,"Contact"],
  "email": [4,"Contact"],
  "impp": [4,"Contact "],
}

/**
 * Javascript implementation of the C++ getAutocompleteInfo() function
 * implemented here:
 * https://searchfox.org/mozilla-central/source/dom/html/HTMLInputElement.cpp#1365
 * based on the specifications detailed here:
 * https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#autofill-processing-model
 * I am ignoring the autofill anchor mantle aspect since this will only
 * be used on fields describing expected input from a user. I also add specific
 * entries in the returned object for section, addressType, and contactType
 * because that is what the C++ method seems to include based on its usage.
 */
function getAutocompleteInfo(element) {
  function defaultInfo() {
    let fieldName = "on"
    const form = element.form;
    if (form && form.getAttribute("autocomplete") === "off") {
      fieldName = "off";
    }
    return {
      hintSet: "",
      scope: "",
      fieldName,
      IDLValue: "",
      section: "",
      addressType: "",
      contactType: "",
    }
  }

  const autocomplete = element.getAttribute("autocomplete");
  if (!autocomplete || autocomplete === "") {
    return defaultInfo();
  }
  const tokens = autocomplete.split(" ");
  if (tokens === []) {
    return defaultInfo();
  }
  let index = tokens.length - 1;
  let field = tokens[index].toLowerCase();
  if (!(field in AUTOFILL_FIELD_NAMES_MAX_TOKENS_AND_CATEGORY)) {
    return defaultInfo();
  }
  const [max_tokens, category] = AUTOFILL_FIELD_NAMES_MAX_TOKENS_AND_CATEGORY[field];
  if (tokens.length > max_tokens) {
    return defaultInfo();
  }

  let section = "";
  let addressType = "";
  let contactType = "";
  let scopeTokens = [];
  let hintTokens = [];
  let IDLValue = field;

  if (category === "Off") {
    return {
      hintSet: hintTokens,
      scope: scopeTokens,
      fieldName: "off",
      IDLValue,
      section,
      contactType,
      addressType,
    }
  }
  if (category === "Automatic") {
    return {
      hintSet: hintTokens,
      scope: scopeTokens,
      fieldName: "on",
      IDLValue,
      section,
      contactType,
      addressType,
    }
  }
  if (index === 0) {
    return {
      hintSet: hintTokens,
      scope: scopeTokens,
      fieldName: field,
      IDLValue,
      section,
      contactType,
      addressType,
    }
  }
  index--;
  if (category === "Contact") {
    const contact = tokens[index].match(/home|work|mobile|fax|pager/i);
    if (contact !== null) {
      contactType = contact[0];
      scopeTokens.unshift(contactType);
      hintTokens.push(contactType);
      IDLValue = contactType + " " + IDLValue;
      if (index === 0) {
        return {
          hintSet: hintTokens,
          scope: scopeTokens,
          fieldName: field,
          IDLValue,
          section,
          contactType,
          addressType,
        }
      }
      index--;
    }
  }
  const mode = tokens[index].match(/shipping|billing/i);
  if (mode !== null) {
    addressType = mode[0];
    scopeTokens.unshift(addressType);
    hintTokens.push(addressType);
    IDLValue = addressType + " " + IDLValue;
    if (index === 0) {
      return {
        hintSet: hintTokens,
        scope: scopeTokens,
        fieldName: field,
        IDLValue,
        section,
        contactType,
        addressType,
      }
    }
    index--;
  }
  if (index !== 0) {
    return defaultInfo();
  }
  if (tokens[index].substr(0, 8).toLowerCase() !== "section-") {
    return defaultInfo();
  }
  section = tokens[index].toLowerCase();
  scopeTokens.unshift(section);
  IDLValue = section + " " + IDLValue;
  return {
    hintSet: hintTokens,
    scope: scopeTokens,
    fieldName: field,
    IDLValue,
    section,
    contactType,
    addressType,
  }
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
