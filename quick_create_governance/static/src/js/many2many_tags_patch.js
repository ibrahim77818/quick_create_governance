/** @odoo-module **/

/**
 * Governs Many2ManyTagsField and its subclasses (color-editable tags,
 * avatar tags...). useActiveActions() recomputes the actions object on every
 * props update, so the restriction is re-applied in an onWillUpdateProps
 * hook registered after core's (OWL runs them in registration order).
 */
import { onWillUpdateProps } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { getQuickCreateRestriction } from "./restriction_registry";

patch(Many2ManyTagsField.prototype, {
    setup() {
        super.setup(...arguments);
        const record = this.props.record;
        this.qcgRestriction = record ? getQuickCreateRestriction(record.resModel, this.props.name) : null;
        if (!this.qcgRestriction) {
            return;
        }
        if (this.qcgRestriction.create) {
            this.quickCreate = null;
        }
        this._qcgApply();
        onWillUpdateProps(() => this._qcgApply());
    },

    _qcgApply() {
        const activeActions = this.activeActions;
        // Native "can create" (view options, create="..." domain, readonly), before governance.
        this.qcgNativeCreate = Boolean(activeActions.create);
        if (this.qcgRestriction.createEdit) {
            activeActions.create = false;
            activeActions.createEdit = false;
        }
        activeActions.qcgRestriction = this.qcgRestriction;
    },

    /**
     * Used by the template extension instead of core's
     * `activeActions.create ? quickCreate : null`, so that blocking only
     * "Create and edit..." (create forced to false) keeps the quick "Create".
     */
    get qcgQuickCreate() {
        if (!this.qcgRestriction) {
            return this.activeActions.create ? this.quickCreate : null;
        }
        if (this.qcgRestriction.create || !this.qcgNativeCreate) {
            return null;
        }
        return this.quickCreate || null;
    },
});
