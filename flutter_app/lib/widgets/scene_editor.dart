import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../models/video_job.dart';

/// Card editable para UNA escena: descripción + diálogo + imagen propia.
class SceneEditor extends StatefulWidget {
  const SceneEditor({
    super.key,
    required this.scene,
    required this.onChanged,
    required this.onRemove,
    this.canRemove = true,
  });

  final SceneInput scene;
  final VoidCallback onChanged;
  final VoidCallback onRemove;
  final bool canRemove;

  @override
  State<SceneEditor> createState() => _SceneEditorState();
}

class _SceneEditorState extends State<SceneEditor> {
  late final TextEditingController _descCtrl;
  late final TextEditingController _dlgCtrl;

  @override
  void initState() {
    super.initState();
    _descCtrl = TextEditingController(text: widget.scene.description);
    _dlgCtrl = TextEditingController(text: widget.scene.dialogue);
  }

  @override
  void dispose() {
    _descCtrl.dispose();
    _dlgCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickImage() async {
    final r = await FilePicker.platform.pickFiles(type: FileType.image);
    if (r != null && r.files.isNotEmpty) {
      final path = r.files.single.path;
      if (path != null) {
        setState(() => widget.scene.referenceImage = File(path));
        widget.onChanged();
      }
    }
  }

  void _removeImage() {
    setState(() => widget.scene.referenceImage = null);
    widget.onChanged();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 16,
                  backgroundColor: theme.colorScheme.primary,
                  child: Text('${widget.scene.sceneNumber}',
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
                const SizedBox(width: 12),
                Text('Escena ${widget.scene.sceneNumber}',
                    style: theme.textTheme.titleMedium),
                const Spacer(),
                if (widget.canRemove)
                  IconButton(
                    tooltip: 'Eliminar escena',
                    icon: const Icon(Icons.delete_outline),
                    onPressed: widget.onRemove,
                  ),
              ],
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _descCtrl,
              decoration: const InputDecoration(
                labelText: 'Descripción de la escena',
                hintText: 'Templo griego al atardecer, columnas de mármol...',
                prefixIcon: Icon(Icons.landscape_outlined),
              ),
              maxLines: 2,
              onChanged: (v) {
                widget.scene.description = v;
                widget.onChanged();
              },
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _dlgCtrl,
              decoration: const InputDecoration(
                labelText: 'Diálogo / narración de esta escena',
                hintText: 'Texto que se va a leer mientras se ve la escena',
                prefixIcon: Icon(Icons.record_voice_over_outlined),
              ),
              maxLines: 3,
              onChanged: (v) {
                widget.scene.dialogue = v;
                widget.onChanged();
              },
            ),
            const SizedBox(height: 12),
            _imageBlock(theme),
          ],
        ),
      ),
    );
  }

  Widget _imageBlock(ThemeData theme) {
    final img = widget.scene.referenceImage;
    if (img == null) {
      return InkWell(
        onTap: _pickImage,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 18),
          decoration: BoxDecoration(
            color: const Color(0xFF14141C),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: theme.colorScheme.primary.withOpacity(0.25),
              width: 1.2,
            ),
          ),
          alignment: Alignment.center,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.add_photo_alternate_outlined,
                  size: 32, color: theme.colorScheme.primary),
              const SizedBox(height: 4),
              const Text('Subir imagen de esta escena'),
              const SizedBox(height: 2),
              Text('Opcional. Sirve de anchor visual para este clip.',
                  style: theme.textTheme.bodySmall),
            ],
          ),
        ),
      );
    }
    return Row(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Image.file(img, width: 110, height: 110, fit: BoxFit.cover),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(img.uri.pathSegments.last,
                  style: theme.textTheme.bodyMedium,
                  maxLines: 1, overflow: TextOverflow.ellipsis),
              const SizedBox(height: 6),
              Wrap(spacing: 8, children: [
                OutlinedButton.icon(
                  onPressed: _pickImage,
                  icon: const Icon(Icons.swap_horiz, size: 18),
                  label: const Text('Cambiar'),
                ),
                OutlinedButton.icon(
                  onPressed: _removeImage,
                  icon: const Icon(Icons.close, size: 18),
                  label: const Text('Quitar'),
                ),
              ]),
            ],
          ),
        ),
      ],
    );
  }
}
