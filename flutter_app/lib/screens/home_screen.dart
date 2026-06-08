import 'dart:io';

import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../widgets/reference_image_picker.dart';
import 'job_progress_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _formKey = GlobalKey<FormState>();
  final _api = ApiService();

  final _titleCtrl = TextEditingController();
  final _sceneCtrl = TextEditingController();
  final _dialogueCtrl = TextEditingController();
  final _voiceIdCtrl = TextEditingController();
  final _styleCtrl = TextEditingController();

  int _clipsCount = 6;
  int _duration = 60;
  bool _generateVoice = true;
  bool _generateVideo = true;
  bool _useReference = false;
  bool _music = false;

  File? _referenceFile;
  bool _submitting = false;

  @override
  void dispose() {
    _titleCtrl.dispose();
    _sceneCtrl.dispose();
    _dialogueCtrl.dispose();
    _voiceIdCtrl.dispose();
    _styleCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _submitting = true);
    try {
      final jobId = await _api.createJob(
        title: _titleCtrl.text.trim(),
        scene: _sceneCtrl.text.trim(),
        dialogue: _dialogueCtrl.text.trim(),
        clipsCount: _clipsCount,
        durationSeconds: _duration,
        generateVoice: _generateVoice,
        generateVideo: _generateVideo,
        useReferenceImage: _useReference,
        voiceId: _voiceIdCtrl.text.trim().isEmpty ? null : _voiceIdCtrl.text.trim(),
        style: _styleCtrl.text.trim().isEmpty ? null : _styleCtrl.text.trim(),
        musicEnabled: _music,
        referenceImage: _useReference ? _referenceFile : null,
      );
      if (!mounted) return;
      Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => JobProgressScreen(jobId: jobId),
      ));
    } on ApiException catch (e) {
      _snack('Error: ${e.message}');
    } catch (e) {
      _snack('Error: $e');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  void _snack(String s) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(s)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Nuevo video'),
        elevation: 0,
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            _sectionTitle('Contenido'),
            TextFormField(
              controller: _titleCtrl,
              decoration: const InputDecoration(
                labelText: 'Título del video',
                prefixIcon: Icon(Icons.title),
              ),
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Requerido' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _sceneCtrl,
              decoration: const InputDecoration(
                labelText: 'Escena general',
                hintText: 'Templo griego al atardecer, iluminación dorada...',
                prefixIcon: Icon(Icons.landscape_outlined),
              ),
              maxLines: 2,
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Requerido' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _dialogueCtrl,
              decoration: const InputDecoration(
                labelText: 'Diálogo / narración',
                hintText: 'Texto completo que se va a leer en off',
                prefixIcon: Icon(Icons.record_voice_over_outlined),
              ),
              maxLines: 6,
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Requerido' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _styleCtrl,
              decoration: const InputDecoration(
                labelText: 'Estilo visual (opcional)',
                hintText: 'cinematic, dark fantasy, gritty realism...',
                prefixIcon: Icon(Icons.palette_outlined),
              ),
            ),

            const SizedBox(height: 28),
            _sectionTitle('Estructura'),
            Row(children: [
              Expanded(child: _numberStepper(
                label: 'Clips',
                value: _clipsCount,
                min: 1, max: 12,
                onChanged: (v) => setState(() => _clipsCount = v),
              )),
              const SizedBox(width: 16),
              Expanded(child: _numberStepper(
                label: 'Duración (s)',
                value: _duration,
                min: 10, max: 120, step: 5,
                onChanged: (v) => setState(() => _duration = v),
              )),
            ]),

            const SizedBox(height: 28),
            _sectionTitle('Imagen referencial'),
            ReferenceImagePicker(
              file: _referenceFile,
              onPicked: (f) => setState(() => _referenceFile = f),
            ),
            SwitchListTile(
              value: _useReference,
              onChanged: (v) => setState(() => _useReference = v),
              title: const Text('Usar imagen como guía visual'),
              subtitle: const Text(
                'Se manda como primer frame al clip 1, y los siguientes '
                'continúan a partir del último frame del anterior.',
              ),
              contentPadding: EdgeInsets.zero,
            ),

            const SizedBox(height: 28),
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
                'Si lo desactivas, los clips serán pantalla negra. Útil para pruebas baratas.',
              ),
              contentPadding: EdgeInsets.zero,
            ),
            SwitchListTile(
              value: _music,
              onChanged: (v) => setState(() => _music = v),
              title: const Text('Mezclar música de fondo'),
              subtitle: const Text(
                'Toma el primer track de la carpeta music/ del backend.',
              ),
              contentPadding: EdgeInsets.zero,
            ),
            TextFormField(
              controller: _voiceIdCtrl,
              decoration: const InputDecoration(
                labelText: 'Voice ID de ElevenLabs (opcional)',
                hintText: 'Sobrescribe el del .env',
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
              label: Text(_submitting ? 'Enviando...' : 'Generar video'),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

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
}
