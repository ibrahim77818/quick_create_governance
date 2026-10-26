# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        """Push the compiled quick-create restriction map into the web client
        session (``session.quick_create_restrictions``).

        Built once per page load / login from an ORM-cached map keyed by the
        user's groups, so no query is spent on rules after the first build
        and no RPC is ever made while users interact with dropdowns."""
        result = super().session_info()
        if request and request.session.uid:
            result["quick_create_restrictions"] = (
                self.env["quick.create.rule"]._get_session_restrictions()
            )
        return result
