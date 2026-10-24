// © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
package com.eliasgt.agenda.alarmas;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.Iterator;

/**
 * Alarmas de AlarmManager para las alertas de reuniones y acuerdos, para que
 * avisen aunque la app este cerrada o en segundo plano (el chequeo de 60s de
 * main.py::_check_alertas solo corre con la app en pantalla).
 *
 * Python (utils/alarmas.py) manda la lista completa de alarmas futuras con
 * reemplazarTodas(); aqui se guardan en SharedPreferences para poder
 * reprogramarlas tras reiniciar el telefono (AlarmManager las borra) sin
 * tener que arrancar Python. Cuando una alarma suena se muestra la
 * notificacion y se anota en "disparadas", que Python lee al volver a la app
 * (consumirDisparadas) para marcar la alerta como enviada y decirla en voz.
 */
public class AlarmasAgenda {
    static final String PREFS = "agenda_alarmas";
    static final String K_PROGRAMADAS = "programadas";  // {clave: {rc, t, ti, tx, v}}
    static final String K_DISPARADAS = "disparadas";    // [{clave, v, t}]
    static final String CANAL = "agenda_alertas";
    static final String ACCION = "com.eliasgt.agenda.ALARMA";
    // Una alarma que debia sonar con el telefono apagado se muestra al
    // encender solo si no paso mas de esto; si no, ya no tiene sentido.
    static final long GRACIA_MS = 10 * 60 * 1000L;

    /** json: [{clave, rc, t (epoch ms), ti, tx, v}] */
    public static synchronized void reemplazarTodas(Context ctx, String json) throws JSONException {
        SharedPreferences prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        JSONObject viejas = new JSONObject(prefs.getString(K_PROGRAMADAS, "{}"));
        for (Iterator<String> it = viejas.keys(); it.hasNext(); ) {
            String clave = it.next();
            cancelarAlarma(ctx, clave, viejas.getJSONObject(clave).optInt("rc"));
        }
        JSONObject nuevas = new JSONObject();
        JSONArray lista = new JSONArray(json);
        for (int i = 0; i < lista.length(); i++) {
            JSONObject a = lista.getJSONObject(i);
            nuevas.put(a.getString("clave"), a);
            programarAlarma(ctx, a.getString("clave"), a.getInt("rc"), a.getLong("t"));
        }
        prefs.edit().putString(K_PROGRAMADAS, nuevas.toString()).apply();
    }

    /** Devuelve las alarmas que sonaron desde la ultima llamada y las borra. */
    public static synchronized String consumirDisparadas(Context ctx) {
        SharedPreferences prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String disparadas = prefs.getString(K_DISPARADAS, "[]");
        prefs.edit().remove(K_DISPARADAS).apply();
        return disparadas;
    }

    static synchronized void disparar(Context ctx, String clave) {
        SharedPreferences prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        try {
            JSONObject programadas = new JSONObject(prefs.getString(K_PROGRAMADAS, "{}"));
            JSONObject a = programadas.optJSONObject(clave);
            if (a == null) {
                return;  // Python la quito despues de programarla (reunion borrada, etc.)
            }
            mostrarNotificacion(ctx, a.getInt("rc"), a.getString("ti"), a.getString("tx"));
            programadas.remove(clave);
            JSONArray disparadas = new JSONArray(prefs.getString(K_DISPARADAS, "[]"));
            disparadas.put(new JSONObject()
                    .put("clave", clave)
                    .put("v", a.optString("v"))
                    .put("t", System.currentTimeMillis()));
            prefs.edit()
                    .putString(K_PROGRAMADAS, programadas.toString())
                    .putString(K_DISPARADAS, disparadas.toString())
                    .apply();
        } catch (JSONException e) {
            // prefs corruptas: nada que mostrar
        }
    }

    /** Tras reiniciar el telefono o actualizar la app. */
    static synchronized void reprogramar(Context ctx) {
        SharedPreferences prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        try {
            JSONObject programadas = new JSONObject(prefs.getString(K_PROGRAMADAS, "{}"));
            long ahora = System.currentTimeMillis();
            JSONArray claves = programadas.names();
            if (claves == null) {
                return;
            }
            JSONArray atrasadas = new JSONArray();
            for (int i = 0; i < claves.length(); i++) {
                String clave = claves.getString(i);
                JSONObject a = programadas.getJSONObject(clave);
                long t = a.getLong("t");
                if (t > ahora) {
                    programarAlarma(ctx, clave, a.getInt("rc"), t);
                } else if (ahora - t < GRACIA_MS) {
                    atrasadas.put(clave);
                } else {
                    programadas.remove(clave);
                }
            }
            // Guardar antes de disparar: disparar() lee y reescribe las
            // mismas prefs, y quita de "programadas" las que muestra.
            prefs.edit().putString(K_PROGRAMADAS, programadas.toString()).apply();
            for (int i = 0; i < atrasadas.length(); i++) {
                disparar(ctx, atrasadas.getString(i));
            }
        } catch (JSONException e) {
            // prefs corruptas: Python reprograma todo al abrir la app
        }
    }

    private static PendingIntent intentAlarma(Context ctx, String clave, int rc, int flags) {
        Intent i = new Intent(ctx, AlarmaReceiver.class).setAction(ACCION).putExtra("clave", clave);
        return PendingIntent.getBroadcast(ctx, rc, i, flags | PendingIntent.FLAG_IMMUTABLE);
    }

    private static void programarAlarma(Context ctx, String clave, int rc, long t) {
        AlarmManager am = (AlarmManager) ctx.getSystemService(Context.ALARM_SERVICE);
        PendingIntent pi = intentAlarma(ctx, clave, rc, PendingIntent.FLAG_UPDATE_CURRENT);
        // Exacta incluso en reposo (Doze) si el sistema lo permite (USE_EXACT_ALARM
        // en el manifest); si no, inexacta -- puede llegar unos minutos tarde.
        if (Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms()) {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, t, pi);
        } else {
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, t, pi);
        }
    }

    private static void cancelarAlarma(Context ctx, String clave, int rc) {
        PendingIntent pi = intentAlarma(ctx, clave, rc, PendingIntent.FLAG_NO_CREATE);
        if (pi != null) {
            ((AlarmManager) ctx.getSystemService(Context.ALARM_SERVICE)).cancel(pi);
            pi.cancel();
        }
    }

    private static void mostrarNotificacion(Context ctx, int rc, String titulo, String texto) {
        NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm.getNotificationChannel(CANAL) == null) {
            NotificationChannel canal = new NotificationChannel(
                    CANAL, "Alertas de reuniones y acuerdos", NotificationManager.IMPORTANCE_HIGH);
            canal.enableVibration(true);
            nm.createNotificationChannel(canal);
        }
        Notification.Builder b = new Notification.Builder(ctx, CANAL)
                .setSmallIcon(ctx.getApplicationInfo().icon)
                .setContentTitle(titulo)
                .setContentText(texto)
                .setStyle(new Notification.BigTextStyle().bigText(texto))
                .setCategory(Notification.CATEGORY_REMINDER)
                .setAutoCancel(true);
        Intent abrir = ctx.getPackageManager().getLaunchIntentForPackage(ctx.getPackageName());
        if (abrir != null) {
            b.setContentIntent(PendingIntent.getActivity(
                    ctx, rc, abrir, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE));
        }
        nm.notify(rc, b.build());
    }
}
