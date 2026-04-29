import { ChangeDetectionStrategy, Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ApiService, MilestoneInfo } from '../../core/services/api.service';

@Component({
  selector: 'pf-dashboard',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="pf-page">
      <header class="pf-page__header">
        <div>
          <h1>Welcome</h1>
          <p class="pf-muted">
            UK-compliant payroll platform — operational view.
          </p>
        </div>
      </header>

      <div class="pf-grid">
        <article class="pf-card pf-card--accent">
          <h3>Current milestone</h3>
          @if (milestone(); as m) {
            <p class="pf-card__headline">#{{ m.milestone }} — {{ m.title }}</p>
            <p class="pf-muted">{{ m.period }} · {{ m.status }}</p>
          } @else if (error()) {
            <p class="pf-error">Could not reach backend: {{ error() }}</p>
          } @else {
            <p class="pf-muted">Loading…</p>
          }
        </article>

        <article class="pf-card">
          <h3>Employees</h3>
          <p class="pf-card__headline">Core record</p>
          <p class="pf-muted">
            NI number, tax code, start date. Pay-bearing fields arrive in M2–M3.
          </p>
        </article>

        <article class="pf-card">
          <h3>HMRC readiness</h3>
          <p class="pf-card__headline">RTI scaffolded</p>
          <p class="pf-muted">FPS / EPS endpoints, P60 &amp; P45 pipelines land in M6–M7.</p>
        </article>

        <article class="pf-card">
          <h3>Compliance</h3>
          <p class="pf-card__headline">UK GDPR baseline</p>
          <p class="pf-muted">Encryption, audit log, RBAC — see docs/.</p>
        </article>
      </div>
    </section>
  `,
  styles: [
    `
      .pf-page {
        max-width: 1100px;
      }

      .pf-page__header h1 {
        margin: 0 0 4px;
        font-size: 26px;
      }

      .pf-muted {
        color: var(--pf-color-ink-muted);
        margin: 0;
      }

      .pf-error {
        color: var(--pf-color-danger);
        margin: 8px 0 0;
      }

      .pf-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 16px;
        margin-top: 24px;
      }

      .pf-card {
        background: var(--pf-color-surface);
        border: 1px solid var(--pf-color-border);
        border-radius: var(--pf-radius);
        padding: 18px 20px;
        box-shadow: var(--pf-shadow);

        h3 {
          margin: 0 0 8px;
          font-size: 12px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: var(--pf-color-ink-muted);
        }
      }

      .pf-card--accent {
        border-top: 3px solid var(--pf-color-accent);
      }

      .pf-card__headline {
        margin: 0 0 4px;
        font-size: 18px;
        font-weight: 600;
      }
    `,
  ],
})
export class DashboardComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly milestone = signal<MilestoneInfo | null>(null);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.api.milestone().subscribe({
      next: (m) => this.milestone.set(m),
      error: (err) => this.error.set(err?.message ?? 'Unknown error'),
    });
  }
}
