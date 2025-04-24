odoo.define('shared_barcode.pos', function (require) {
    'use strict';

    const models = require('point_of_sale.models');
    const screens = require('point_of_sale.screens');
    const core = require('web.core');
    const _t = core._t;
    const Dialog = require('web.Dialog');
    
    const _super_barcode_reader = models.BarcodeReader.prototype;
    
    // Extender el lector de códigos de barras para manejar variantes
    models.BarcodeReader = models.BarcodeReader.extend({
        scan: function(code) {
            const self = this;
            const parsed_result = this.barcode_parser.parse_barcode(code);
            
            // Si es un código de producto
            if (parsed_result.type === 'product') {
                // Obtener el producto usando una llamada al servidor que soporta variantes
                return this.pos.rpc({
                    model: 'pos.config',
                    method: '_get_product_by_barcode',
                    args: [this.pos.config.id, code],
                }).then(function(result) {
                    if (!result) {
                        return self.gui.show_popup('error', {
                            'title': _t('Invalid Barcode'),
                            'body':  _t('The barcode could not be found.'),
                        });
                    }
                    
                    // Si el resultado contiene múltiples variantes, mostrar un selector
                    if (result.multiple_variants) {
                        self._show_variant_selection_popup(result, code);
                    } else {
                        // Comportamiento normal para un solo producto
                        return _super_barcode_reader.scan.call(self, code);
                    }
                });
            } else {
                // Para otros tipos de códigos, usar el comportamiento predeterminado
                return _super_barcode_reader.scan.call(this, code);
            }
        },
        
        _show_variant_selection_popup: function(result, barcode) {
            const self = this;
            
            // Crear un diálogo con las variantes disponibles
            new Dialog(this, {
                title: _t('Seleccionar Variante'),
                size: 'medium',
                buttons: _.map(result.variants, function(variant) {
                    return {
                        text: variant.name + ' (' + variant.combination_name.join(', ') + ')',
                        classes: 'btn-primary',
                        close: true,
                        click: function() {
                            // Cuando se selecciona una variante, obtener ese producto y añadirlo al pedido
                            const product = self.pos.db.get_product_by_id(variant.id);
                            if (product) {
                                self.pos.get_order().add_product(product);
                            }
                        }
                    };
                }).concat([{
                    text: _t('Cancelar'),
                    close: true
                }]),
                $content: $('<div>').html(
                    _t('Se encontraron múltiples variantes con el código de barras: ') + barcode + 
                    _t('. Por favor, seleccione la variante correcta.')
                ),
            }).open();
        }
    });
    
    // Extender el modelo de producto para incluir la información del template
    const _super_models = models.PosModel.prototype.models;
    models.PosModel.prototype.models.forEach(function(model) {
        if (model.model === 'product.product') {
            const _super_product_loaded = model.loaded;
            model.loaded = function(self, products) {
                // Llamar al cargador original
                _super_product_loaded.call(this, self, products);
                
                // Añadir una referencia al template_id en cada producto
                for (let i = 0; i < products.length; i++) {
                    const product = products[i];
                    self.db.product_by_id[product.id].product_tmpl_id = product.product_tmpl_id;
                }
            };
        }
    });
    
    return {
        BarcodeReader: models.BarcodeReader,
    };
});