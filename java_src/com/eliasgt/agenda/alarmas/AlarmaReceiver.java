// © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
package com.eliasgt.agenda.alarmas;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * Recibe las alarmas programadas por AlarmasAgenda (corre sin Python, aunque
 * la app este cerrada) y el reinicio del telefono / actualizacion de la app,
 * que borran todas las alarmas de AlarmManager. Declarado en el manifest por
 * scripts/patch_p4a.py (parche #6).
 */
public class AlarmaReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context ctx, Intent intent) {
        String accion = intent.getAction();
        if (Intent.ACTION_BOOT_COMPLETED.equals(accion)
                || Intent.ACTION_MY_PACKAGE_REPLACED.equals(accion)) {
            AlarmasAgenda.reprogramar(ctx);
        } else if (AlarmasAgenda.ACCION.equals(accion)) {
            String clave = intent.getStringExtra("clave");
            if (clave != null) {
                AlarmasAgenda.disparar(ctx, clave);
            }
        }
    }
}
