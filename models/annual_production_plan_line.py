from odoo import models, fields, api

class AnnualProductionPlanLine(models.Model):
    _name = 'annual.production.plan.line'
    _description = 'Annual Production Plan Line'

    plan_id = fields.Many2one('annual.production.plan', required=True, ondelete='cascade')
    date = fields.Date(required=True)
    planned_quantity = fields.Float(required=True)
    actual_quantity = fields.Float(readonly=True, compute='compute_actuals', store=True)
    achievement = fields.Float(readonly=True, compute='compute_actuals', store=True)
    remark = fields.Text()
    invisible_id = fields.Char(default=lambda self: self.env['ir.sequence'].next_by_code('plan.line.invisible'))

    @api.depends('date', 'plan_id.product_id')
    def compute_actuals(self):
        for line in self:
            mo_domain = [
                ('product_id', '=', line.plan_id.product_id.id),
                ('state', '=', 'done'),
                ('date_start', '<=', line.date),
                ('date_finished', '>=', line.date)
            ]
            mos = self.env['mrp.production'].search(mo_domain)
            actual_qty = sum(mo.qty_produced for mo in mos)
            downtime = 0
            for mo in mos:
                if hasattr(mo, 'x_studio_one2many_field_RcsDL'):
                    downtime += sum(rec.x_studio_downtimemin for rec in mo.x_studio_one2many_field_RcsDL if hasattr(rec, 'x_studio_downtimemin'))

            line.actual_quantity = actual_qty
            line.achievement = (actual_qty / line.planned_quantity * 100) if line.planned_quantity > 0 else 0
