/** @odoo-module **/

/**
 * Odoo 16 still ships the legacy (widget-based) FieldMany2One for views that
 * have not been converted to OWL (some Enterprise / third-party legacy views,
 * legacy many2many_tags which embeds a FieldMany2One). Same rule, same map.
 */
import relationalFields from "web.relational_fields";
import { getQuickCreateRestriction } from "./restriction_registry";

relationalFields.FieldMany2One.include({
    init() {
        this._super(...arguments);
        const restriction = getQuickCreateRestriction(this.model, this.name);
        if (!restriction) {
            return;
        }
        // Clone: nodeOptions is shared with the parsed arch node.
        this.nodeOptions = Object.assign({}, this.nodeOptions);
        if (restriction.create) {
            this.nodeOptions.no_quick_create = true;
        }
        if (restriction.createEdit) {
            this.nodeOptions.no_create_edit = true;
        }
        if (restriction.create && restriction.createEdit) {
            this.can_create = false;
        }
    },

    _getSearchCreatePopupOptions() {
        const options = this._super(...arguments);
        const restriction = getQuickCreateRestriction(this.model, this.name);
        if (restriction && restriction.createEdit) {
            options.no_create = true; // "Create" button of the legacy SelectCreateDialog
        }
        return options;
    },

    _quickCreate() {
        const restriction = getQuickCreateRestriction(this.model, this.name);
        if (restriction && restriction.create) {
            return Promise.resolve();
        }
        return this._super(...arguments);
    },
});
