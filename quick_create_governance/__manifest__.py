# -*- coding: utf-8 -*-
{
    "name": "Quick Create Governance",
    "version": "18.0.1.0.0",
    "summary": "Centrally block 'Create' / 'Create and edit...' on chosen models and "
               "relational fields, with session-cached rules and zero runtime RPC.",
    "description": """
Quick Create Governance
=======================
Lets administrators decide, from one configuration screen, on which models and
relational fields (many2one / many2many) users may create records on the fly.

* Rules target a model and, optionally, specific many2one / many2many fields
  (no field selected = every relational field of the model).
* Separate switches for the quick "Create" option and for
  "Create and edit..." (which also hides the "New" button of the
  "Search More..." dialog).
* Per-rule exempt groups.
* The compiled rule map is ORM-cached server side and pushed once into the
  web client session info: dropdown interactions perform no extra RPC.
* Enforcement is purely subtractive: restricted fields lose creation
  options whatever the XML / Studio options say, unconfigured fields keep
  native behaviour (including their own no_create / no_create_edit options).
* Works with Community and Enterprise (OWL relational fields).
""",
    "author": "Ibrahim Yahia",
    "website": "https://www.linkedin.com/in/ibrahim-yahia",
    "category": "Technical",
    "license": "LGPL-3",
    "images": ["static/description/banner.png"],
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/quick_create_rule_views.xml",
    ],
    "demo": [
        "demo/quick_create_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "quick_create_governance/static/src/js/restriction_registry.js",
            "quick_create_governance/static/src/js/many2x_autocomplete_patch.js",
            "quick_create_governance/static/src/js/many2one_patch.js",
            "quick_create_governance/static/src/js/many2many_tags_patch.js",
            "quick_create_governance/static/src/js/x2many_patch.js",
            "quick_create_governance/static/src/xml/many2many_tags.xml",
        ],
        "web.assets_tests": [
            "quick_create_governance/static/tests/tours/quick_create_tours.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
