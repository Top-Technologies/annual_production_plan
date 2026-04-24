from odoo import models, fields, api
import datetime

class AnnualProductionPlanLine(models.Model):
    _name = 'annual.production.plan.line'
    _description = 'Annual Production Plan Line'

    plan_id = fields.Many2one('annual.production.plan', required=True, ondelete='cascade')
    date = fields.Date(required=True)
    planned_quantity = fields.Float(required=True)
    actual_quantity = fields.Float(readonly=True, compute='compute_actuals', store=True)
    achievement = fields.Float(readonly=True, compute='compute_actuals', store=True)
    difference = fields.Float(readonly=True, compute='compute_actuals', store=True)
    remark = fields.Text()
    invisible_id = fields.Char(default=lambda self: self.env['ir.sequence'].next_by_code('plan.line.invisible'))

    @api.depends('date', 'plan_id.product_id')
    def compute_actuals(self):
        for line in self:
            print(f"DEBUG: Computing actuals for line date={line.date}, product={line.plan_id.product_id.name}")
            mo_domain = [
                ('product_id', '=', line.plan_id.product_id.id),
                ('state', '=', 'done'),
                ('date_start', '>=', line.date),  # MO started on or after this day
                ('date_start', '<', line.date + datetime.timedelta(days=1))  # MO started before next day
            ]
            print(f"DEBUG: MO domain: {mo_domain}")
            mos = self.env['mrp.production'].search(mo_domain)
            print(f"DEBUG: Found {len(mos)} MOs")
            
            # Also try searching for MOs on the same date (ignoring time)
            if not mos:
                print(f"DEBUG: No MOs found with exact date match, trying broader search...")
                broader_domain = [
                    ('product_id', '=', line.plan_id.product_id.id),
                    ('state', '=', 'done'),
                ]
                all_mos = self.env['mrp.production'].search(broader_domain)
                print(f"DEBUG: Found {len(all_mos)} total MOs for this product")
                for mo in all_mos:
                    print(f"DEBUG: MO {mo.name}: date_start={mo.date_start}, date_finished={mo.date_finished}, x_annual_plan_qty={mo.x_annual_plan_qty}")
            
            actual_qty = sum(mo.qty_produced for mo in mos)
            downtime = 0
            for mo in mos:
                if hasattr(mo, 'x_studio_one2many_field_RcsDL'):
                    downtime += sum(rec.x_studio_downtimemin for rec in mo.x_studio_one2many_field_RcsDL if hasattr(rec, 'x_studio_downtimemin'))

            line.actual_quantity = actual_qty
            line.achievement = (actual_qty / line.planned_quantity) if line.planned_quantity > 0 else 0
            line.difference = (actual_qty - line.planned_quantity) if line.planned_quantity > 0 else 0
