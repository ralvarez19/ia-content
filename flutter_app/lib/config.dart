import 'package:shared_preferences/shared_preferences.dart';

/// Configuración del cliente con persistencia.
///
/// La URL del backend se guarda en SharedPreferences para que el usuario
/// pueda cambiarla desde Settings SIN tener que recompilar el APK.
///
/// Defaults:
/// - Si la app corre en el MISMO PC que el backend  → http://127.0.0.1:8000
/// - Si corre en celular conectado a la misma red WiFi
///   → http://<IP-LAN-de-tu-PC>:8000 (configurable en Settings)
/// - Si corre en Android Emulator del PC          → http://10.0.2.2:8000
class AppConfig {
  static const String _kBaseUrl = 'backend_base_url';
  static const String _kPollSecs = 'progress_poll_seconds';

  /// Default que se usa la primera vez que abrís la app.
  /// 192.168.1.118 era la IP previa, pero el router puede haberte asignado
  /// otra; revisá Settings → "Probar conexión" cuando abras la app.
  static const String defaultBaseUrl = 'http://192.168.1.118:8000';

  static String backendBaseUrl = defaultBaseUrl;
  static int progressPollSeconds = 2;

  static Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    backendBaseUrl = prefs.getString(_kBaseUrl) ?? defaultBaseUrl;
    progressPollSeconds = prefs.getInt(_kPollSecs) ?? 2;
  }

  static Future<void> saveBaseUrl(String url) async {
    backendBaseUrl = url.trim();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kBaseUrl, backendBaseUrl);
  }

  static Future<void> resetBaseUrl() async {
    backendBaseUrl = defaultBaseUrl;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kBaseUrl);
  }
}
