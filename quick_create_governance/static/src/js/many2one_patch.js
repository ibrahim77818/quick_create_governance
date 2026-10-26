/** @odoo-module **/

/**
 * Governs Many2OneField and, through inheritance, every widget built on it
 * (many2one_avatar, res_partner_many2one, list/kanban many2one, Enterprise
 * and Studio variants...).
 *
 * The restriction is resolved once in setup() (resModel + field name never
 * change for a mounted field) and applied each time core recomputes the
 * active actions, i.e. AFTER the view options (no_create, no_create_edit,
 * no_quick_create, can_create) have been evaluated: governance can only
 * remove capabilities, never re-grant them.
 */
import { patch } from "@web/core/utils/patch";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { getQuickCreateRestriction } from "./restriction_registry";

patch(Many2OneField.prototype, {
    setup() {
        const record = this.props.record;
        // Must be known before super.setup(), which calls computeActiveActions().
        this.qcgRestriction = record ? getQuickCreateRestriction(record.resModel, this.props.name) : null;
        super.setup(...arguments);
        if (this.qcgRestriction && this.qcgRestriction.create) {
            // Many2XAutocomplete only offers "Create <text>" when it gets a quickCreate callback.
            this.quickCreate = null;
        }
    },

    computeActiveActions(props) {
        super.computeActiveActions(...arguments);
        const restriction = this.qcgRestriction;
        if (!restriction) {
            return;
        }
        const activeActions = this.state.activeActions;
        if (restriction.createEdit) {
            // `create` drives the "New" button of SelectCreateDialog
            // (noCreate: !activeActions.create) and creation in the form dialog.
            activeActions.create = false;
            activeActions.createEdit = false;
        }
        activeActions.qcgRestriction = restriction;
    },

    async openConfirmationDialog(request) {
        if (this.qcgRestriction && this.qcgRestriction.create) {
            return;
        }
        return super.openConfirmationDialog(...arguments);
    },
});
