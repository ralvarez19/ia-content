import 'package:flutter/material.dart';

import '../config.dart';
import '../services/api_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _urlCtrl = TextEditingController(text: AppConfig.backendBaseUrl);
  final _api = ApiService();
  Map<String, dynamic>? _lastTest;
  bool _testing = false;

  @override
  void dispose() {
    _urlCtrl.dispose();
    super.dispose();
  }

  Future<void> _saveAndTest() async {
    final url = _urlCtrl.text.trim();
    if (url.isEmpty) return;
    await AppConfig.saveBaseUrl(url);
    await _test();
  }

  Future<void> _test() async {
    setState(() {
      _testing = true;
      _lastTest = null;
    });
    final r = await _api.testConnection();
    if (!mounted) return;
    setState(() {
      _testing = false;
      _lastTest = r;
    });
  }

  Future<void> _reset() async {
    await AppConfig.resetBaseUrl();
    _urlCtrl.text = AppConfig.backendBaseUrl;
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Conexión al backend')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('URL del backend',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _urlCtrl,
                    decoration: const InputDecoration(
                      hintText: 'http://192.168.1.100:8000',
                      prefixIcon: Icon(Icons.link),
                    ),
                    keyboardType: TextInputType.url,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Ejemplos:\n'
                    '• http://127.0.0.1:8000  (mismo PC)\n'
                    '• http://192.168.1.118:8000  (PC en la LAN, real ip)\n'
                    '• http://10.0.2.2:8000  (Android emulator del mismo PC)',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 16),
                  Wrap(spacing: 12, runSpacing: 8, children: [
                    FilledButton.icon(
                      onPressed: _testing ? null : _saveAndTest,
                      icon: _testing
                          ? const SizedBox(
                              width: 16, height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.cloud_sync_outlined),
                      label: const Text('Guardar y probar'),
                    ),
                    OutlinedButton.icon(
                      onPressed: _testing ? null : _test,
                      icon: const Icon(Icons.cloud_done_outlined),
                      label: const Text('Probar ahora'),
                    ),
                    TextButton.icon(
                      onPressed: _reset,
                      icon: const Icon(Icons.restart_alt),
                      label: const Text('Restablecer'),
                    ),
                  ]),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          if (_lastTest != null) _resultCard(_lastTest!),
          const SizedBox(height: 16),
          _helpCard(),
        ],
      ),
    );
  }

  Widget _resultCard(Map<String, dynamic> r) {
    final ok = r['ok'] == true;
    return Card(
      color: ok
          ? Colors.greenAccent.withOpacity(0.08)
          : Colors.redAccent.withOpacity(0.08),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(ok ? Icons.check_circle : Icons.error,
                  color: ok ? Colors.greenAccent : Colors.redAccent),
              const SizedBox(width: 8),
              Text(
                ok ? 'Conexión OK · ${r['latencyMs']} ms'
                   : 'Conexión fallida',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ]),
            const SizedBox(height: 8),
            if (ok && r['data'] is Map) ...[
              _kv('Host', '${r['data']['host']}:${r['data']['port']}'),
              _kv('IPs locales del server',
                  (r['data']['local_ips'] as List?)?.join(', ') ?? '—'),
              const SizedBox(height: 6),
              Text('Servicios configurados:',
                  style: Theme.of(context).textTheme.bodySmall),
              ...((r['data']['services'] as Map?)?.entries
                      .map((e) => _kv('  • ${e.key}', e.value.toString())) ??
                  const []),
            ],
            if (!ok)
              Text(r['error']?.toString() ?? 'Error desconocido',
                  style: const TextStyle(
                      color: Colors.redAccent, fontFamily: 'monospace')),
          ],
        ),
      ),
    );
  }

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(children: [
          SizedBox(width: 170,
              child: Text(k, style: Theme.of(context).textTheme.bodySmall)),
          Expanded(child: Text(v)),
        ]),
      );

  Widget _helpCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('¿No conecta?', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 10),
            _bullet('1. En tu PC arrancá uvicorn con --host 0.0.0.0 '
                '(no 127.0.0.1).'),
            _bullet('2. En tu PC corré (PowerShell admin) la regla de firewall:'
                '\n   New-NetFirewallRule -DisplayName "ia-content" '
                '-Direction Inbound -LocalPort 8000 -Protocol TCP '
                '-Action Allow -Profile Private'),
            _bullet('3. Verificá que el celular esté en la misma WiFi que '
                'el PC.'),
            _bullet('4. Abrí en el browser del cel <baseUrl>/health: '
                'si ves JSON, conecta; si timeout, es firewall o WiFi.'),
            _bullet('5. La IP del PC puede cambiar (DHCP). Llamá a /health '
                'desde el browser y mirá "local_ips" para saber cuál usar.'),
          ],
        ),
      ),
    );
  }

  Widget _bullet(String s) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(s, style: Theme.of(context).textTheme.bodyMedium),
      );
}
