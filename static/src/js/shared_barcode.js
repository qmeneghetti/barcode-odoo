odoo.define('shared_barcode.pos', function (require) {
    'use strict';
    
    const { _t } = require('web.core');
    const { Gui } = require('point_of_sale.Gui');
    const BarcodeReader = require('point_of_sale.BarcodeReader');
    const { patch } = require('web.utils');
    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useState, useContext } = owl.hooks;
    const { usePos } = require('point_of_sale.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    
    // Parche para el BarcodeReader para manejar códigos de barras compartidos
    patch(BarcodeReader.prototype, 'shared_barcode.BarcodeReader', {
        /**
         * @override
         */
        async _barcodeProductAction(code) {
            const self = this;
            const product = await this._getProductByBarcode(code);
            
            if (!product) {
                return;
            }
            
            // Si el resultado es un objeto con multiple_variants, mostrar un selector
            if (product.multiple_variants) {
                this._showVariantSelectionPopup(product, code);
                return true;
            }
            
            // Llamada al método original para productos individuales
            return this._super(...arguments);
        },
        
        /**
         * Método personalizado para obtener productos por código de barras con soporte para variantes
         */
        async _getProductByBarcode(code) {
            try {
                const result = await this.pos.env.services.rpc({
                    model: 'pos.config',
                    method: '_get_product_by_barcode',
                    args: [this.pos.config.id, code],
                });
                return result;
            } catch (error) {
                console.error('Error al buscar producto por código de barras:', error);
                Gui.showPopup('ErrorPopup', {
                    title: _t('Error de Red'),
                    body: _t('No se pudo verificar el código de barras. Compruebe su conexión e inténtelo de nuevo.')
                });
                return null;
            }
        },
        
        /**
         * Muestra un popup para seleccionar entre variantes de producto
         */
        _showVariantSelectionPopup(result, barcode) {
            const self = this;
            const list = result.variants.map(variant => ({
                id: variant.id,
                label: variant.name + (variant.combination_name.length ? ` (${variant.combination_name.join(', ')})` : ''),
                item: variant
            }));
            
            Gui.showPopup('SelectionPopup', {
                title: _t('Seleccionar Variante'),
                list: list,
                confirmText: _t('Añadir'),
                cancelText: _t('Cancelar'),
                onselect: async (variant) => {
                    const product = this.pos.db.get_product_by_id(variant.id);
                    if (product) {
                        const order = this.pos.get_order();
                        order.add_product(product);
                    } else {
                        // Si el producto no está en la base de datos local, intentar cargarlo
                        try {
                            const productData = await this.pos.env.services.rpc({
                                model: 'product.product',
                                method: 'read',
                                args: [[variant.id]],
                            });
                            if (productData && productData.length) {
                                // Añadir el producto a la base de datos y al pedido
                                this.pos.db.add_products([productData[0]]);
                                const product = this.pos.db.get_product_by_id(variant.id);
                                if (product) {
                                    const order = this.pos.get_order();
                                    order.add_product(product);
                                }
                            }
                        } catch (error) {
                            console.error('Error al cargar el producto:', error);
                            Gui.showPopup('ErrorPopup', {
                                title: _t('Error'),
                                body: _t('No se pudo cargar el producto seleccionado.')
                            });
                        }
                    }
                }
            });
        }
    });
    
    // Extender el hook de inicialización del POS para cargar información de template_id
    const PosModelExtend = (PosGlobalState) => class PosModelExtend extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            
            // Añadir información de template_id a los productos
            const products = loadedData['product.product'];
            if (products) {
                for (const product of products) {
                    const productObj = this.db.get_product_by_id(product.id);
                    if (productObj) {
                        productObj.product_tmpl_id = product.product_tmpl_id;
                    }
                }
            }
        }
    };
    
    Registries.Model.extend('pos.global.state', PosModelExtend);
    
    return {
        BarcodeReader
    };
});