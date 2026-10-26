/** @odoo-module **/

import { registry } from "@web/core/registry";

/*
 * Data and rules are created by tests/test_ui.py. The test form view shows:
 *   parent_id    governed  (Create + Create and edit blocked), XML says no_create: False
 *   category_id  governed  (many2many_tags, both blocked)
 *   user_id      governed  (only "Create and edit" blocked)
 *   title        NOT governed (native: both options available)
 *   industry_id  NOT governed, XML no_create: True (native option must still apply)
 */

const field = (name) => `.o_form_view .o_field_widget[name="${name}"]`;
const dropdown = (name) => `${field(name)} .o-autocomplete--dropdown-menu`;
const check = (content, trigger) => ({ content, trigger, run() {} });

const REGISTRY_MODULE = "@quick_create_governance/js/restriction_registry";
const LOOKUPS = 100000;
const LATENCY_BUDGET_MS = 250; // ~1000x slack over a typical run (< 1µs per lookup)

/** The governance check runs once per field mount and is a pure in-memory
 *  lookup: assert it stays far below anything a user could perceive. */
const latencyStep = {
    content: "Restriction lookup has no measurable latency",
    trigger: ".o_form_view",
    run() {
        const lookup = odoo.loader.modules.get(REGISTRY_MODULE);
        if (!lookup) {
            console.error(`${REGISTRY_MODULE} is not loaded`);
            return;
        }
        const start = performance.now();
        for (let i = 0; i < LOOKUPS; i++) {
            lookup.getQuickCreateRestriction("res.partner", i % 2 ? "parent_id" : "title");
        }
        const elapsed = performance.now() - start;
        if (elapsed > LATENCY_BUDGET_MS) {
            console.error(`${LOOKUPS} restriction lookups took ${elapsed.toFixed(1)}ms`);
        } else {
            console.log(`${LOOKUPS} restriction lookups: ${elapsed.toFixed(2)}ms`);
        }
    },
};

function typeIn(name, text) {
    return {
        content: `Type "${text}" in ${name}`,
        trigger: `${field(name)} input`,
        run: `text ${text}`,
    };
}

function noCreationOptions(name) {
    return check(
        `${name}: no creation entry in the dropdown`,
        `${dropdown(name)}:not(:has(.o_m2o_dropdown_option_create)):not(:has(.o_m2o_dropdown_option_create_edit))`
    );
}

registry.category("web_tour.tours").add("quick_create_governance_restricted", {
    test: true,
    steps: () => [
        {
            content: "Form is ready",
            trigger: `${field("name")} input`,
            run: "text QCR Tour Partner",
        },
        latencyStep,

        // 1. Governed many2one overriding an explicit XML no_create: False
        typeIn("parent_id", "QCR Nomatch"),
        check("parent_id: 'No records' shown", `${dropdown("parent_id")} .o_m2o_no_result`),
        noCreationOptions("parent_id"),

        // 2. "Search More..." dialog must lose its "New" button
        typeIn("parent_id", "QCR Seed"),
        {
            content: "Open Search More",
            trigger: `${dropdown("parent_id")} .o_m2o_dropdown_option_search_more`,
        },
        check("Dialog list is loaded", ".modal .o_list_view .o_data_row"),
        check(
            "SelectCreateDialog has no 'New' button",
            ".modal .modal-footer:has(.o_form_button_cancel):not(:has(.o_create_button))"
        ),
        {
            content: "Close the dialog",
            trigger: ".modal .modal-footer .o_form_button_cancel",
        },
        check("Dialog closed", "body:not(:has(.modal .o_list_view))"),

        // 3. Ungoverned field keeps native behaviour
        typeIn("title", "QCR New Title"),
        check("title: native Create", `${dropdown("title")} .o_m2o_dropdown_option_create`),
        check("title: native Create and edit", `${dropdown("title")} .o_m2o_dropdown_option_create_edit`),

        // 4. Ungoverned field with XML no_create keeps its native restriction
        typeIn("industry_id", "QCR Nomatch Industry"),
        check("industry_id: XML no_create still honoured", `${dropdown("industry_id")} .o_m2o_no_result`),
        noCreationOptions("industry_id"),

        // 5. Governed many2many_tags
        typeIn("category_id", "QCR Nomatch Tag"),
        check("category_id: 'No records' shown", `${dropdown("category_id")} .o_m2o_no_result`),
        noCreationOptions("category_id"),

        // 6. Partial rule: only "Create and edit" blocked
        typeIn("user_id", "QCR Nomatch User"),
        check("user_id: quick Create kept", `${dropdown("user_id")} .o_m2o_dropdown_option_create`),
        check(
            "user_id: no Create and edit, no misleading 'No records'",
            `${dropdown("user_id")}:not(:has(.o_m2o_dropdown_option_create_edit)):not(:has(.o_m2o_no_result))`
        ),
    ],
});

registry.category("web_tour.tours").add("quick_create_governance_exempt", {
    test: true,
    steps: () => [
        {
            content: "Form is ready",
            trigger: `${field("name")} input`,
            run: "text QCR Exempt Partner",
        },
        typeIn("parent_id", "QCR Nomatch"),
        check("Exempt user: Create available", `${dropdown("parent_id")} .o_m2o_dropdown_option_create`),
        check(
            "Exempt user: Create and edit available",
            `${dropdown("parent_id")} .o_m2o_dropdown_option_create_edit`
        ),
    ],
});
