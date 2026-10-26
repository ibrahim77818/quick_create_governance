# -*- coding: utf-8 -*-
import json

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "quick_create_governance")
class TestQuickCreateGovernanceUi(HttpCase):
    """End-to-end checks in a real browser (web tours) plus the session payload.

    The dedicated form view below exercises every situation the module must
    handle; see static/tests/tours/quick_create_tours.js for the steps."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        Rule = env["quick.create.rule"]
        # Isolate from pre-existing (e.g. demo) rules; rolled back after the class.
        Rule.search([]).write({"active": False})
        env.registry.clear_cache()
        cls.partner_model = env["ir.model"]._get("res.partner")
        fields = {
            name: env["ir.model.fields"]._get("res.partner", name)
            for name in ("parent_id", "category_id", "user_id")
        }

        # > searchLimit (7) matches so that "Search More..." is offered.
        env["res.partner"].create([
            {"name": "QCR Seed %02d" % i, "is_company": True} for i in range(1, 11)
        ])

        cls.view = env["ir.ui.view"].create({
            "name": "res.partner.form.qcr.test",
            "model": "res.partner",
            "type": "form",
            "mode": "primary",
            "priority": 999,
            "arch": """
                <form>
                    <sheet>
                        <group>
                            <field name="name"/>
                            <field name="parent_id" options="{'no_create': False, 'no_create_edit': False}"/>
                            <field name="category_id" widget="many2many_tags"/>
                            <field name="user_id"/>
                            <field name="title"/>
                            <field name="industry_id" options="{'no_create': True}"/>
                        </group>
                    </sheet>
                </form>
            """,
        })
        cls.action = env["ir.actions.act_window"].create({
            "name": "QCR Test Partners",
            "res_model": "res.partner",
            "view_mode": "form",
            "view_id": cls.view.id,
            "target": "current",
        })

        cls.rule_full = Rule.create({
            "model_id": cls.partner_model.id,
            "field_ids": [(6, 0, [fields["parent_id"].id, fields["category_id"].id])],
            "block_quick_create": True,
            "block_create_edit": True,
        })
        cls.rule_partial = Rule.create({
            "model_id": cls.partner_model.id,
            "field_ids": [(6, 0, fields["user_id"].ids)],
            "block_quick_create": False,
            "block_create_edit": True,
        })
        cls.url = "/odoo/action-%d/new" % cls.action.id

    @classmethod
    def tearDownClass(cls):
        cls.env.registry.clear_cache()
        super().tearDownClass()

    def _session_info(self):
        response = self.url_open(
            "/web/session/get_session_info",
            data=json.dumps({"jsonrpc": "2.0", "method": "call", "id": 1, "params": {}}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotIn("error", payload, payload.get("error"))
        return payload["result"]

    def test_01_session_info_carries_compiled_map(self):
        self.authenticate("admin", "admin")
        restrictions = self._session_info()["quick_create_restrictions"]
        partner_map = restrictions["res.partner"]
        self.assertEqual(partner_map["parent_id"], {"create": True, "create_edit": True})
        self.assertEqual(partner_map["category_id"], {"create": True, "create_edit": True})
        self.assertEqual(partner_map["user_id"], {"create": False, "create_edit": True})
        self.assertNotIn("title", partner_map)
        self.assertNotIn("industry_id", partner_map)

    def test_02_tour_restricted_and_native_fields(self):
        self.start_tour(self.url, "quick_create_governance_restricted", login="admin")

    def test_03_tour_exempt_group(self):
        group = self.env["res.groups"].create({"name": "QCR Tour Exempt"})
        self.rule_full.exempt_group_ids = [(6, 0, group.ids)]
        self.env.ref("base.user_admin").group_ids = [(4, group.id)]
        self.authenticate("admin", "admin")
        self.assertNotIn("parent_id",
                         self._session_info()["quick_create_restrictions"].get("res.partner", {}))
        self.start_tour(self.url, "quick_create_governance_exempt", login="admin")
