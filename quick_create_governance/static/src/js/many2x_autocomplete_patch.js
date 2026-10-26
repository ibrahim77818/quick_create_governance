/** @odoo-module **/

/**
 * Safety net on the shared autocomplete used by many2one, many2many_tags and
 * every widget extending them. The host field patches mark the activeActions
 * object they hand down with `qcgRestriction`; here we make sure no creation
 * entry survives in the dropdown, whatever a subclass passed as props.
 * Ungoverned widgets (no marker) are returned untouched.
 */
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

const CREATE_CLASS = "o_m2o_dropdown_option_create";
const CREATE_EDIT_CLASS = "o_m2o_dropdown_option_create_edit";
const NO_RESULT_CLASS = "o_m2o_no_result";
const START_TYPING_CLASS = "o_m2o_start_typing";

function hasClass(option, cls) {
    return typeof option.classList === "string" && option.classList.split(/\s+/).includes(cls);
}

patch(Many2XAutocomplete.prototype, {
    async loadOptionsSource(request) {
        const options = await super.loadOptionsSource(...arguments);
        const restriction = this.props.activeActions && this.props.activeActions.qcgRestriction;
        if (!restriction) {
            return options;
        }
        let result = options.filter((option) => {
            if (restriction.create && hasClass(option, CREATE_CLASS)) {
                return false;
            }
            if (restriction.createEdit && hasClass(option, CREATE_EDIT_CLASS)) {
                return false;
            }
            return true;
        });
        const canStillCreate = result.some(
            (o) => hasClass(o, CREATE_CLASS) || hasClass(o, CREATE_EDIT_CLASS)
        );
        if (canStillCreate) {
            // A creation entry survives (e.g. only "Create and edit" blocked):
            // never show "No records" next to it.
            result = result.filter((o) => !hasClass(o, NO_RESULT_CLASS));
        } else {
            // Nothing can be created any more: "Start typing..." is pointless.
            result = result.filter((o) => !hasClass(o, START_TYPING_CLASS));
            const hasRecords = result.some((o) => !o.action && !o.unselectable);
            if (request.length && !hasRecords && !result.some((o) => hasClass(o, NO_RESULT_CLASS))) {
                result.push({
                    label: _t("No records"),
                    classList: NO_RESULT_CLASS,
                    unselectable: true,
                });
            }
        }
        return result;
    },
});
