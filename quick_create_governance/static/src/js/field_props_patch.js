/**
 * Since Odoo 19 the many2one widget is split into a thin field wrapper (Many2OneField,
 * Many2OneAvatarField, Many2OneBarcodeField...) that forwards its props to a
 * shared `Many2One` component which no longer knows the host record. The one
 * place that still knows record + field for every widget is the generic
 * `Field` component, which builds the widget props from the view node.
 *
 * We therefore govern many2one fields there: AFTER the view options
 * (no_create, no_create_edit, no_quick_create, can_create) have been turned
 * into props, the restriction can only switch them off, never back on.
 *
 *   restriction.create     -> canQuickCreate = false   ("Create <text>")
 *   restriction.createEdit -> canCreateEdit  = false   ("Create and edit...")
 *                             canCreate      = false   ("New" in Search more dialog)
 *
 * In Odoo 19/20 the quick "Create" entry only depends on canQuickCreate, so
 * blocking "Create and edit..." alone keeps quick create available.
 * many2many widgets are handled by many2many_tags_patch.js / x2many_patch.js.
 */
import { patch } from "@web/core/utils/patch";
import { Field } from "@web/views/fields/field";
import { getQuickCreateRestriction } from "./restriction_registry";

patch(Field.prototype, {
    get fieldComponentProps() {
        const props = super.fieldComponentProps;
        const record = this.props.record;
        if (!record || this.type !== "many2one") {
            return props;
        }
        const restriction = getQuickCreateRestriction(record.resModel, this.props.name);
        if (!restriction) {
            return props;
        }
        // Odoo 20 (OWL 3) components declare props with useProps() instead of a
        // static schema, so only override keys the widget's extractProps produced:
        // that guarantees the widget accepts them.
        if (restriction.create && "canQuickCreate" in props) {
            props.canQuickCreate = false;
        }
        if (restriction.createEdit) {
            if ("canCreateEdit" in props) {
                props.canCreateEdit = false;
            }
            if ("canCreate" in props) {
                props.canCreate = false;
            }
        }
        return props;
    },
});
