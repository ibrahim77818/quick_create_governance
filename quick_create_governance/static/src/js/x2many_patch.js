/** @odoo-module **/

/**
 * Many2many fields displayed as a list / kanban ("Add a line" opens a
 * SelectCreateDialog). When "Create and edit..." is blocked, the dialog keeps
 * selecting existing records but loses its "New" button. One2many fields are
 * never touched: they are not quick-create fields.
 */
import { onWillUpdateProps } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { getQuickCreateRestriction } from "./restriction_registry";

patch(X2ManyField.prototype, {
    setup() {
        super.setup(...arguments);
        if (!this.isMany2Many || !this.props.record) {
            return;
        }
        const restriction = getQuickCreateRestriction(this.props.record.resModel, this.props.name);
        if (!restriction || !restriction.createEdit) {
            return;
        }
        const apply = () => {
            // Keep "Add a line" (driven by `link`) but forbid creation in the dialog.
            if (!("link" in this.activeActions)) {
                this.activeActions.link = this.activeActions.create;
            }
            this.activeActions.create = false;
            this.activeActions.createEdit = false;
            this.activeActions.qcgRestriction = restriction;
        };
        apply();
        onWillUpdateProps(() => apply());
    },
});
