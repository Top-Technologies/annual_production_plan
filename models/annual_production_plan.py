from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta, date

class AnnualProductionPlan(models.Model):
    _name = 'annual.production.plan'
    _description = 'Annual Production Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True)
    product_id = fields.Many2one('product.product', string='Product', 
                               domain="[('type', '=', 'product')]", required=True)
    planned_by_id = fields.Many2one('res.users', default=lambda self: self.env.user, 
                                  required=True)

    date = fields.Date(string="Date")
    planned_quantity = fields.Float(string="Planned Quantity")
    actual_quantity = fields.Float(string="Actual Quantity")
    achievement = fields.Float(string="Achievement")
    remark = fields.Text(string="Remark")
    approver_ids = fields.Many2many(
        'res.users', 
        'annual_plan_approver_rel',
        'plan_id', 'user_id',
        string='Approvers',
        required=True
    )
    approved_by_ids = fields.Many2many(
        'res.users', 
        'annual_plan_approved_by_rel',
        'plan_id', 'user_id',
        string='Approved By',
        readonly=True
    )
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    daily_production_plan = fields.Float(string="Daily Production Target", required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, 
                               required=True)
    state = fields.Selection([
        ('draft', 'Draft'), 
        ('confirmed', 'Confirmed'), 
        ('done', 'Done')
    ], default='draft', tracking=True)
    line_ids = fields.One2many('annual.production.plan.line', 'plan_id', 
                             string='Daily Plans')

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date > rec.end_date:
                raise ValidationError(_("End date cannot be before start date"))
            if (rec.end_date - rec.start_date).days > 366:
                raise ValidationError(_("Plan duration cannot exceed one year"))

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft plans can be confirmed.'))
            if not rec.line_ids:
                rec._generate_daily_lines()
            rec.state = 'confirmed'

    def action_approve(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_('Only confirmed plans can be approved.'))
            if self.env.user not in rec.approver_ids:
                raise UserError(_('You are not among the approvers.'))

            rec.approved_by_ids = [(4, self.env.uid)]
            if set(rec.approver_ids.ids).issubset(set(rec.approved_by_ids.ids)):
                rec.state = 'done'

    def _generate_daily_lines(self):
        self.ensure_one()
        lines = []
        current = self.start_date
        end_date = self.end_date
        
        while current <= end_date:
            if date.weekday(current) != 6:
                lines.append((0, 0, {
                    'date': current,
                    'planned_quantity': self.daily_production_plan,
                }))
            current += timedelta(days=1)
        
        self.write({'line_ids': lines})

    def action_compute_actuals(self):
        for plan in self:
            for line in plan.line_ids:
                mo_domain = [
                    ('product_id', '=', plan.product_id.id),
                    ('state', '=', 'done'),
                    ('date_start', '<=', line.date),
                    ('date_finished', '>=', line.date)
                ]
                mos = self.env['mrp.production'].search(mo_domain)
                actual_qty = sum(mo.qty_produced for mo in mos)               
                line.write({
                    'actual_quantity': actual_qty,
                    'achievement': (actual_qty / line.planned_quantity * 100) if line.planned_quantity > 0 else 0,
                })