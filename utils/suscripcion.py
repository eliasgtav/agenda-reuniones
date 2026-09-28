# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Suscripción de pago (mensual/anual) vía Google Play Billing. El trial de
15 días gratis NO se cuenta a mano aquí -- se configura como oferta del
plan en Play Console, y Google lo maneja por cuenta de Google (no por
dispositivo, así que desinstalar/reinstalar la app no lo reinicia).

Solo funciona en Android (usa sjbillingclient, un wrapper de la Google Play
Billing Library vía pyjnius) -- en Windows (modo desarrollo) esta_activa()
siempre da True para no bloquear el flujo de trabajo normal.

Mensual y anual son DOS PRODUCTOS DE SUSCRIPCIÓN separados en Play Console
(no un producto con dos "base plans") -- evita tener que elegir un offerToken
específico al lanzar la compra, cada uno con su propia oferta de prueba de
15 días. Los IDs de abajo son provisionales: hay que confirmarlos con los
que se hayan creado de verdad en Play Console antes de publicar.
"""
from datetime import datetime, timedelta
from kivy.utils import platform
from utils.config import cargar, guardar

IDS_SUSCRIPCION = {
    'mensual': 'suscripcion_mensual',
    'anual': 'suscripcion_anual',
}

# Cuanto se deja usar la app sin poder confirmar la suscripcion con Google
# Play (sin internet, o Play Services no disponible) antes de exigir
# reconectarse -- balance entre no dejar a alguien sin agenda en una reunion
# sin señal, y no dejar "activa para siempre" una suscripcion vencida que
# nunca se vuelve a verificar.
GRACIA_DIAS_OFFLINE = 5

# Purchase.PurchaseState de la Billing Library -- una compra PENDING (pago en
# efectivo/transferencia aun no confirmado) no da acceso ni se puede
# reconocer todavia; solo PURCHASED cuenta.
_ESTADO_COMPRADA = 1

_billing_client = None
# True apenas Play Billing responde de verdad en ESTA sesion (activa o no) --
# permite distinguir "se acaba de confirmar en linea" de "se esta confiando
# en el ultimo estado guardado porque ahora mismo no hay como verificar".
_verificado_esta_sesion = False


def iniciar(on_cambio_estado=None):
    """Conecta con Google Play Billing y revisa el estado real de la
    suscripcion. No hace nada fuera de Android. on_cambio_estado() se llama
    (sin argumentos) cada vez que se actualiza el estado cacheado.

    Seguro de llamar mas de una vez (p.ej. main.py en on_start Y en cada
    on_resume, para revalidar cuando la app vuelve de segundo plano) --
    si ya hay una conexion abierta, solo se repite la consulta de compras
    en vez de abrir una conexion nueva y perder la anterior sin cerrarla."""
    global _billing_client
    if platform != 'android':
        return
    if _billing_client is not None:
        _revisar_compras(on_cambio_estado)
        return
    try:
        from sjbillingclient.tools import BillingClient
        from sjbillingclient.jclass.billing import BillingResponseCode

        def _en_compras_actualizadas(billing_result, is_null, purchases):
            if billing_result.getResponseCode() == BillingResponseCode.OK and not is_null:
                _reconocer_pendientes(purchases)
            _revisar_compras(on_cambio_estado)

        _billing_client = BillingClient(on_purchases_updated=_en_compras_actualizadas)

        def _al_conectar(billing_result):
            if billing_result.getResponseCode() == BillingResponseCode.OK:
                _revisar_compras(on_cambio_estado)

        _billing_client.start_connection(
            on_billing_setup_finished=_al_conectar,
            on_billing_service_disconnected=lambda: None,
        )
    except Exception:
        pass


def _reconocer_pendientes(purchases):
    # Una suscripcion sin "acknowledge" en los primeros 3 dias, Google la
    # reembolsa sola -- hay que confirmarla apenas se detecta, tanto recien
    # comprada (aqui) como si ya existia pero por algun motivo (la app se
    # cerro a medias) no habia quedado reconocida (ver _revisar_compras).
    try:
        for purchase in purchases:
            if purchase.getPurchaseState() == _ESTADO_COMPRADA and not purchase.isAcknowledged():
                _billing_client.acknowledge_purchase(purchase.getPurchaseToken(), lambda r: None)
    except Exception:
        pass


def _hay_compra_vigente(purchases):
    try:
        return any(p.getPurchaseState() == _ESTADO_COMPRADA for p in purchases)
    except Exception:
        return False


def _revisar_compras(on_cambio_estado=None):
    try:
        from sjbillingclient.jclass.billing import ProductType, BillingResponseCode

        def _resultado(billing_result, purchases):
            global _verificado_esta_sesion
            try:
                ok = billing_result.getResponseCode() == BillingResponseCode.OK
            except Exception:
                ok = False
            if not ok:
                # Sin respuesta valida (sin red, Play Services caido) NO se
                # toca el cache -- sobreescribirlo con False aqui anularia el
                # periodo de gracia offline justo cuando hace falta.
                if on_cambio_estado:
                    on_cambio_estado()
                return
            _verificado_esta_sesion = True
            activa = bool(purchases) and _hay_compra_vigente(purchases)
            if activa:
                _reconocer_pendientes(purchases)
            config = cargar()
            config['suscripcion_activa'] = activa
            config['suscripcion_ultima_verificacion'] = datetime.now().isoformat()
            try:
                guardar(config)
            except OSError:
                pass
            if on_cambio_estado:
                on_cambio_estado()

        _billing_client.query_purchase_async(
            product_type=ProductType.SUBS,
            on_query_purchases_response=_resultado,
        )
    except Exception:
        if on_cambio_estado:
            on_cambio_estado()


def esta_activa():
    """Lectura rapida (sin red) del estado cacheado -- es lo que consulta el
    resto de la app para decidir si mostrar la pantalla de suscripcion."""
    if platform != 'android':
        return True
    config = cargar()
    if not config.get('suscripcion_activa'):
        return False
    ultima = config.get('suscripcion_ultima_verificacion', '')
    if not ultima:
        return False
    try:
        momento = datetime.fromisoformat(ultima)
    except ValueError:
        return False
    return (datetime.now() - momento) <= timedelta(days=GRACIA_DIAS_OFFLINE)


def en_gracia_offline():
    """True si la app se esta dejando usar confiando en el ultimo estado
    guardado, sin haber podido reconfirmar con Google Play en esta sesion
    (sin internet, o Play Services no disponible) -- para avisarle al
    usuario en la pantalla de suscripcion. No es lo mismo que
    'esta_activa() es False', que es cuando la gracia ya se agoto."""
    if platform != 'android' or _verificado_esta_sesion:
        return False
    return esta_activa()


def consultar_precios(on_precios):
    """on_precios(dict) con el precio formateado por plan (los que se hayan
    podido consultar; un plan ausente del dict significa que no se pudo
    traer su precio -- la pantalla debe mostrar un texto generico en ese
    caso, no asumir que siempre llegan los 2)."""
    if platform != 'android' or _billing_client is None:
        on_precios({})
        return
    try:
        from sjbillingclient.jclass.billing import ProductType, BillingResponseCode

        def _con_detalles(billing_result, product_details_result):
            precios = {}
            try:
                if billing_result.getResponseCode() == BillingResponseCode.OK:
                    productos = product_details_result.getProductDetailsList()
                    ids_por_producto = {v: k for k, v in IDS_SUSCRIPCION.items()}
                    for producto in productos:
                        plan = ids_por_producto.get(producto.getProductId())
                        if not plan:
                            continue
                        ofertas = producto.getSubscriptionOfferDetails()
                        if not ofertas or ofertas.isEmpty():
                            continue
                        fases = ofertas.get(0).getPricingPhases().getPricingPhaseList()
                        # La primera fase suele ser el trial (precio 0) -- se
                        # muestra el precio de la fase recurrente (la ultima).
                        fase_pago = fases.get(fases.size() - 1)
                        precios[plan] = fase_pago.getFormattedPrice()
            except Exception:
                pass
            on_precios(precios)

        _billing_client.query_product_details_async(
            product_type=ProductType.SUBS,
            products_ids=list(IDS_SUSCRIPCION.values()),
            on_product_details_response=_con_detalles,
        )
    except Exception:
        on_precios({})


def comprar(plan, on_resultado=None):
    """plan: 'mensual' o 'anual' (ver IDS_SUSCRIPCION)."""
    if platform != 'android' or _billing_client is None:
        if on_resultado:
            on_resultado(False, 'Las suscripciones solo están disponibles en la app de Android.')
        return
    producto_id = IDS_SUSCRIPCION.get(plan)
    if not producto_id:
        if on_resultado:
            on_resultado(False, f'Plan desconocido: {plan}')
        return
    try:
        from sjbillingclient.jclass.billing import ProductType, BillingResponseCode

        def _con_detalles(billing_result, product_details_result):
            try:
                if billing_result.getResponseCode() != BillingResponseCode.OK:
                    if on_resultado:
                        on_resultado(False, 'No se pudo conectar con Google Play.')
                    return
                productos = product_details_result.getProductDetailsList()
                if not productos or productos.isEmpty():
                    if on_resultado:
                        on_resultado(False, 'Este plan no está disponible todavía.')
                    return
                _lanzar_en_hilo_ui(productos)
            except Exception as e:
                if on_resultado:
                    on_resultado(False, f'Error al iniciar la compra: {e}')

        _billing_client.query_product_details_async(
            product_type=ProductType.SUBS,
            products_ids=[producto_id],
            on_product_details_response=_con_detalles,
        )
    except Exception as e:
        if on_resultado:
            on_resultado(False, f'Error: {e}')


def _lanzar_en_hilo_ui(productos):
    # launchBillingFlow() tiene que correr en el hilo de UI de Android, y el
    # callback de queryProductDetailsAsync llega en un hilo de fondo de la
    # Billing Library.
    from android.runnable import run_on_ui_thread

    @run_on_ui_thread
    def _lanzar():
        try:
            _billing_client.launch_billing_flow(product_details=productos)
        except Exception:
            pass
    _lanzar()


def abrir_gestion_suscripcion():
    """Abre la pantalla de Play Store donde el usuario cancela/cambia su
    suscripcion -- Play exige que esto pase por su propia UI, una app no
    puede implementar su propio flujo de cancelacion."""
    if platform != 'android':
        return
    try:
        from jnius import autoclass
        Intent = autoclass('android.content.Intent')
        Uri = autoclass('android.net.Uri')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        paquete = PythonActivity.mActivity.getPackageName()
        url = f'https://play.google.com/store/account/subscriptions?package={paquete}'
        intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        PythonActivity.mActivity.startActivity(intent)
    except Exception:
        pass
