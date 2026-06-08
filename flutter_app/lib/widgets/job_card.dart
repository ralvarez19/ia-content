import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/video_job.dart';

class JobCard extends StatelessWidget {
  const JobCard({
    super.key,
    required this.summary,
    required this.onOpen,
    required this.onDownload,
  });

  final JobSummary summary;
  final VoidCallback onOpen;
  final VoidCallback onDownload;

  Color _statusColor(BuildContext ctx) {
    switch (summary.status) {
      case JobStatus.completed: return Colors.greenAccent;
      case JobStatus.failed:    return Colors.redAccent;
      case JobStatus.running:   return Colors.amberAccent;
      case JobStatus.queued:    return Colors.blueGrey;
    }
  }

  String _formatDate(String iso) {
    try {
      final dt = DateTime.parse(iso).toLocal();
      return DateFormat('dd MMM yyyy · HH:mm').format(dt);
    } catch (_) {
      return iso;
    }
  }

  @override
  Widget build(BuildContext context) {
    final canDownload = summary.status == JobStatus.completed;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 10, height: 60,
              decoration: BoxDecoration(
                color: _statusColor(context),
                borderRadius: BorderRadius.circular(5),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    summary.title.isEmpty ? '(sin título)' : summary.title,
                    style: Theme.of(context).textTheme.titleMedium,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${summary.status.name.toUpperCase()} · ${summary.progress}%',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  Text(
                    _formatDate(summary.createdAt),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            IconButton(
              tooltip: 'Ver progreso',
              icon: const Icon(Icons.visibility_outlined),
              onPressed: onOpen,
            ),
            IconButton(
              tooltip: 'Abrir video',
              icon: const Icon(Icons.play_circle_outline),
              onPressed: canDownload ? onDownload : null,
            ),
          ],
        ),
      ),
    );
  }
}
