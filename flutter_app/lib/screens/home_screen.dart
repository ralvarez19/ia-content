import 'package:flutter/material.dart';

import '../models/video_job.dart';
import '../services/api_service.dart';
import '../widgets/scene_editor.dart';
import 'job_progress_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _api = ApiService();
  final _titleCtrl = TextEditingController();
  final _voiceIdCtrl = TextEditingController();
  final _styleCtrl = TextEditingController();

  final List<SceneInput> _scenes = [
    SceneInput(sceneNumber: 1),
    SceneInput(sceneNumber: 2),
    SceneInput(sceneNumber: 3),
  ];

  int _duration = 60;
  bool _generateVoice = true;
  bool _generateVideo = true;
  bool _music = false;
  bool _submitting = false;

  bool? _backendOk;

  @override
  void initState() {
    super.initState();
    _pingBackend();
  }

  @override
  void dispose() {
    _titleCtrl.dispose();
    _voiceIdCtrl.dispose();
    _styleCtrl.dispose();
    super.dispose();
  }

  Future<void> _pingBackend() async {
    final r = await _api.testConnection(timeout: const Duration(seconds: 3));
    if (!mounted) return;
    setState(() => _backendOk = r['ok'] == true);
  }

  void _addScene() {
    setState(() {
      _scenes.add(SceneInput(sceneNumber: _scenes.length + 1));
    });
  }

  void _removeScene(int index) {
    setState(() {
      _scenes.removeAt(index);
      for (int i = 0; i < _scenes.length; i++) {
        _scenes[i].sceneNumber = i + 1;
      }
    });
  }

  String? _validate() {
    if (_titleCtrl.text.trim().isEmpty) return 'Falta el título';
    if (_scenes.isEmpty) return 'Necesitás al menos 1 escena';
    for (int i = 0; i < _scenes.length; i++) {
      final s = _scenes[i];
      if (s.description.trim().isEmpty) {
        return 'Escena ${i + 1}: falta la descripción';
      }
      if (s.dialogue.trim().isEmpty) {
        return 'Escena ${i + 1}: falta el diálogo';
      }
    }
    return null;
  }

  Future<void> _submit() async {
    final err = _validate();
    if (err != null) {
      _snack(err);
      return;
    }
    setState(() => _submitting = true);
    try {
      final jobId = await _api.createJob(
        title: _titleCtrl.text.trim(),
        scenes: _scenes,
        durationSeconds: _duration,
        generateVoice: _generateVoice,
        generateVideo: _generateVideo,
        voiceId: _voiceIdCtrl.text.trim().isEmpty ? null : _voiceIdCtrl.text.trim(),
        style: _styleCtrl.text.trim().isEmpty ? null : _styleCtrl.text.trim(),
        musicEnabled: _music,
      );
      if (!mounted) return;
      Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => JobProgressScreen(jobId: jobId),
      ));
    } on ApiException catch (e) {
      _snack('Error ${e.statusCode}: ${e.message}');
    } catch (e) {
      _snack('Error: $e');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  void _snack(String s) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(s), duration: const Duration(seconds: 5)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Nuevo video'),
        actions: [
          IconButton(
            tooltip: 'Conexión',
            icon: Icon(
              _backendOk == null
                  ? Icons.cloud_outlined
                  : (_backendOk! ? Icons.cloud_done : Icons.cloud_off),
              color: _backendOk == null
                  ? null
                  : (_backendOk! ? Colors.greenAccent : Colors.redAccent),
            ),
            onPressed: () async {
              await Navigator.push(context, MaterialPageRoute(
                builder: (_) => const SettingsScreen(),
              ));
              _pingBackend();
            },
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (_backendOk == false) _offlineBanner(),

          _sectionTitle('General'),
          TextField(
            controller: _titleCtrl,
            decoration: const InputDecoration(
              labelText: 'Título del video',
              prefixIcon: Icon(Icons.title),
            ),
          ),
          const SizedBox(height: 14),
          Row(children: [
            Expanded(child: _numberStepper(
              label: 'Duración (s)',
              value: _duration,
              min: 10, max: 240, step: 5,
              onChanged: (v) => setState(() => _duration = v),
            )),
            const SizedBox(width: 12),
            Expanded(child: _readonlyStat(
              label: 'Escenas',
              value: '${_scenes.length}',
            )),
          ]),

          const SizedBox(height: 24),
          _sectionTitle('Escenas'),
          ..._scenes.asMap().entries.map((e) {
            final i = e.key;
            return Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: SceneEditor(
                key: ValueKey('scene_${e.value.sceneNumber}_$i'),
                scene: e.value,
                onChanged: () => setState(() {}),
                onRemove: () => _removeScene(i),
                canRemove: _scenes.length > 1,
              ),
            );
          }),
          OutlinedButton.icon(
            onPressed: _scenes.length < 12 ? _addScene : null,
            icon: const Icon(Icons.add),
            label: Text(_scenes.length < 12
                ? 'Agregar escena (${_scenes.length}/12)'
                : 'Máximo 12 escenas'),
          ),

          const SizedBox(height: 24),
          _sectionTitle('Generación'),
          SwitchListTile(
            value: _generateVoice,
            onChanged: (v) => setState(() => _generateVoice = v),
            title: const Text('Generar voz (ElevenLabs)'),
            contentPadding: EdgeInsets.zero,
          ),
          SwitchListTile(
            value: _generateVideo,
            onChanged: (v) => setState(() => _generateVideo = v),
            title: const Text('Generar clips de video (Veo)'),
            subtitle: const Text(
              'Si lo apagás: clips negros + tu narración. Útil para probar barato.',
            ),
            contentPadding: EdgeInsets.zero,
          ),
          SwitchListTile(
            value: _music,
            onChanged: (v) => setState(() => _music = v),
            title: const Text('Mezclar música de fondo'),
            subtitle: const Text(
              'Usa el primer archivo de music/ del backend.',
            ),
            contentPadding: EdgeInsets.zero,
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _styleCtrl,
            decoration: const InputDecoration(
              labelText: 'Estilo visual (opcional)',
              hintText: 'cinematic, dark fantasy, gritty realism...',
              prefixIcon: Icon(Icons.palette_outlined),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _voiceIdCtrl,
            decoration: const InputDecoration(
              labelText: 'Voice ID ElevenLabs (opcional)',
              prefixIcon: Icon(Icons.mic_none_outlined),
            ),
          ),

          const SizedBox(height: 28),
          FilledButton.icon(
            onPressed: _submitting ? null : _submit,
            icon: _submitting
                ? const SizedBox(
                    width: 18, height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.movie_filter_outlined),
            label: Text(_submitting ? 'Subiendo...' : 'Generar video'),
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _offlineBanner() => Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.redAccent.withOpacity(0.12),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Colors.redAccent.withOpacity(0.4)),
        ),
        child: Row(
          children: [
            const Icon(Icons.cloud_off, color: Colors.redAccent),
            const SizedBox(width: 12),
            const Expanded(
              child: Text(
                'No puedo conectar con el backend. Andá a Conexión y revisá la URL.',
              ),
            ),
            TextButton(
              onPressed: () async {
                await Navigator.push(context, MaterialPageRoute(
                  builder: (_) => const SettingsScreen(),
                ));
                _pingBackend();
              },
              child: const Text('Abrir'),
            ),
          ],
        ),
      );

  Widget _sectionTitle(String s) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Text(s, style: Theme.of(context).textTheme.titleMedium),
      );

  Widget _numberStepper({
    required String label,
    required int value,
    required int min,
    required int max,
    required ValueChanged<int> onChanged,
    int step = 1,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF14141C),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: Theme.of(context).textTheme.bodySmall),
                Text('$value', style: Theme.of(context).textTheme.titleLarge),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.remove_circle_outline),
            onPressed: value > min ? () => onChanged(value - step) : null,
          ),
          IconButton(
            icon: const Icon(Icons.add_circle_outline),
            onPressed: value < max ? () => onChanged(value + step) : null,
          ),
        ],
      ),
    );
  }

  Widget _readonlyStat({required String label, required String value}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF14141C),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          Text(value, style: Theme.of(context).textTheme.titleLarge),
        ],
      ),
    );
  }
}
