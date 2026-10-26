/**
 * Read-only access to the restriction map compiled server side and shipped in
 * the session info (see models/ir_http.py). Lookups are two property reads:
 * no RPC, no async work, nothing that could add latency to a dropdown.
 *
 * Map shape:
 *   { "<model>": { "<field>" | "*": { create: bool, create_edit: bool } } }
 */
import { session } from "@web/session";

export const WILDCARD = "*";

let restrictionMap = session.quick_create_restrictions || {};

/**
 * @param {string} resModel  model of the record hosting the field
 * @param {string} fieldName relational field name
 * @returns {{create: boolean, createEdit: boolean} | null}
 *   `create`     → hide the quick "Create <text>" option
 *   `createEdit` → hide "Create and edit..." and the dialog "New" button
 *   `null`       → field not governed: native behaviour, untouched
 */
export function getQuickCreateRestriction(resModel, fieldName) {
    const modelMap = resModel && restrictionMap[resModel];
    if (!modelMap) {
        return null;
    }
    const specific = modelMap[fieldName];
    const wildcard = modelMap[WILDCARD];
    if (!specific && !wildcard) {
        return null;
    }
    const restriction = {
        create: Boolean((specific && specific.create) || (wildcard && wildcard.create)),
        createEdit: Boolean(
            (specific && specific.create_edit) || (wildcard && wildcard.create_edit)
        ),
    };
    return restriction.create || restriction.createEdit ? restriction : null;
}

/** Test helper: swap the map (QUnit / tours). Not used in production code. */
export function _setQuickCreateRestrictionMap(map) {
    restrictionMap = map || {};
}
