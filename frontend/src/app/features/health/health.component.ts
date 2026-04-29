import { ChangeDetectionStrategy, Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ApiService, HealthStatus } from '../../core/services/api.service';

@Component({
  selector: 'pf-health',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="pf-page">
      <h1>System health</h1>
      <p class="pf-muted">Live probe against the backend API.</p>

      @if (status(); as s) {
        <div class="pf-panel pf-panel--ok">
          <h3>Backend</h3>
          <dl>
            <dt>Status</dt><dd>{{ s.status }}</dd>
            <dt>Version</dt><dd>{{ s.version }}</dd>
            <dt>Environment</dt><dd>{{ s.environment }}</dd>
          </dl>
        </div>
      } @else if (error()) {
        <div class="pf-panel pf-panel--err">
          <h3>Backend unreachable</h3>
          <p>{{ error() }}</p>
        </div>
      } @else {
        <p class="pf-muted">Checking…</p>
      }
    </section>
  `,
  styles: [
    `
      .pf-page {
        max-width: 640px;
      }

      h1 {
        margin: 0 0 4px;
      }

      .pf-muted {
        color: var(--pf-color-ink-muted);
        margin: 0 0 24px;
      }

      .pf-panel {
        background: var(--pf-color-surface);
        border: 1px solid var(--pf-color-border);
        border-radius: var(--pf-radius);
        padding: 20px 24px;
        box-shadow: var(--pf-shadow);

        h3 {
          margin: 0 0 12px;
          font-size: 14px;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: var(--pf-color-ink-muted);
        }
      }

      .pf-panel--ok {
        border-left: 4px solid var(--pf-color-accent);
      }

      .pf-panel--err {
        border-left: 4px solid var(--pf-color-danger);
        color: var(--pf-color-danger);
      }

      dl {
        display: grid;
        grid-template-columns: 140px 1fr;
        gap: 6px 16px;
        margin: 0;
        font-size: 14px;
      }

      dt {
        color: var(--pf-color-ink-muted);
      }
    `,
  ],
})
export class HealthComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly status = signal<HealthStatus | null>(null);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.api.health().subscribe({
      next: (s) => this.status.set(s),
      error: (err) => this.error.set(err?.message ?? 'Unknown error'),
    });
  }
}
