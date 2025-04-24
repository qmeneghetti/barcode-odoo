from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    shared_barcode = fields.Char(
        string='Código de Barras Compartido',
        help='Este código de barras será compartido entre todas las variantes de este producto'
    )
    
    use_shared_barcode = fields.Boolean(
        string='Usar código de barras compartido',
        help='Si está marcado, todas las variantes usarán el mismo código de barras'
    )
    
    @api.onchange('use_shared_barcode')
    def _onchange_use_shared_barcode(self):
        """Actualiza las variantes cuando se activa el código de barras compartido"""
        if self.use_shared_barcode and self.shared_barcode:
            # Si activamos el código compartido, actualizamos todas las variantes
            for variant in self.product_variant_ids:
                variant.barcode = self.shared_barcode
        elif not self.use_shared_barcode:
            # Si desactivamos el código compartido, limpiamos los códigos de barras de las variantes
            for variant in self.product_variant_ids:
                variant.barcode = False
    
    @api.onchange('shared_barcode')
    def _onchange_shared_barcode(self):
        """Actualiza las variantes cuando cambia el código de barras compartido"""
        if self.use_shared_barcode and self.shared_barcode:
            for variant in self.product_variant_ids:
                variant.barcode = self.shared_barcode


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # Sobrescribimos el método de restricción de unicidad del código de barras
    _sql_constraints = [
        ('barcode_uniq', "CHECK(1=1)", "Un código de barras puede ser compartido entre variantes del mismo producto."),
    ]
    
    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        """Permite códigos de barras duplicados solo entre variantes del mismo producto"""
        for product in self:
            if not product.barcode:
                continue
                
            # Si el producto usa código compartido, permitimos duplicados dentro del mismo template
            if product.product_tmpl_id.use_shared_barcode:
                continue
                
            # Buscamos productos con el mismo código de barras pero que no sean variantes del mismo template
            domain = [
                ('barcode', '=', product.barcode),
                ('id', '!=', product.id),
                '|',
                ('product_tmpl_id', '!=', product.product_tmpl_id.id),
                ('product_tmpl_id.use_shared_barcode', '=', False)
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(_(
                    'El código de barras %s ya está siendo utilizado por otro producto que no es una variante del mismo template.'
                ) % product.barcode)


class PosSession(models.Model):
    _inherit = 'pos.session'
    
    def _loader_params_product_product(self):
        """Extender el cargador de productos para incluir información sobre el código compartido"""
        result = super()._loader_params_product_product()
        if 'search_params' in result and 'fields' in result['search_params']:
            if 'product_tmpl_id' not in result['search_params']['fields']:
                result['search_params']['fields'].append('product_tmpl_id')
        return result


class PosConfig(models.Model):
    _inherit = 'pos.config'
    
    @api.model
    def _get_product_by_barcode(self, barcode):
        """Método para buscar productos por código de barras con soporte para variantes compartidas"""
        # Comprueba primero si hay un producto único con este código de barras
        products = self.env['product.product'].search([
            ('barcode', '=', barcode),
            ('available_in_pos', '=', True)
        ])
        
        if not products:
            return None
            
        if len(products) == 1:
            # Solo hay un producto con este código, devolvemos ese
            return products[0].id
        else:
            # Hay múltiples productos (variantes) con este código
            # Verificamos si pertenecen al mismo template
            templates = products.mapped('product_tmpl_id')
            if len(templates) == 1 and templates.use_shared_barcode:
                # Si son variantes del mismo producto y usan código compartido,
                # devolvemos un diccionario especial para mostrar un selector de variantes
                return {
                    'multiple_variants': True,
                    'template_id': templates.id,
                    'variants': [{
                        'id': p.id,
                        'name': p.display_name,
                        'combination_name': p.product_template_attribute_value_ids.mapped('name'),
                    } for p in products]
                }
            else:
                # Si hay conflicto (múltiples productos de diferentes templates),
                # devolvemos el primero
                return products[0].id