import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';

import { ApiService, MilestoneInfo, PayrollFramework, Tenant } from '../../core/services/api.service';

@Component({
  selector: 'pf-dashboard',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="pf-page">
      <header class="pf-page__header">
        <div>
          <h1>Payroll control room</h1>
          <p class="pf-muted">
            UK-compliant payroll platform with Milestone 2 foundations enabled.
          </p>
        </div>
      </header>

      <div class="pf-grid">
        <article class="pf-card pf-card--accent">
          <h3>Current milestone</h3>
          @if (milestone(); as m) {
            <p class="pf-card__headline">#{{ m.milestone }} - {{ m.title }}</p>
            <p class="pf-muted">{{ m.period }} - {{ m.status }}</p>
          } @else if (error()) {
            <p class="pf-error">Could not reach backend: {{ error() }}</p>
          } @else {
            <p class="pf-muted">Loading...</p>
          }
        </article>

        <article class="pf-card">
          <h3>Tenants</h3>
          <p class="pf-card__headline">{{ tenants().length }}</p>
          <p class="pf-muted">Employer isolation, PAYE references and default pay frequency.</p>
        </article>

        <article class="pf-card">
          <h3>RBAC</h3>
          <p class="pf-card__headline">{{ framework()?.roles?.length ?? 0 }} roles</p>
          <p class="pf-muted">Tenant owner, payroll admin, viewer and self-service profiles.</p>
        </article>

        <article class="pf-card">
          <h3>Payroll framework</h3>
          <p class="pf-card__headline">{{ framework()?.pay_frequencies?.length ?? 0 }} frequencies</p>
          <p class="pf-muted">Weekly, fortnightly, four-weekly and monthly HMRC-ready setup.</p>
        </article>

        <article class="pf-card">
          <h3>Security hardening</h3>
          <p class="pf-card__headline">Headers + CSRF</p>
          <p class="pf-muted">CSP, HSTS, frame protection, content sniffing guard and CSRF gate.</p>
        </article>

        <article class="pf-card">
          <h3>Idempotency</h3>
          <p class="pf-card__headline">Create-safe API</p>
          <p class="pf-muted">Tenant, employee and contract creation support Idempotency-Key.</p>
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
  readonly tenants = signal<Tenant[]>([]);
  readonly framework = signal<PayrollFramework | null>(null);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.api.milestone().subscribe({
      next: (m) => this.milestone.set(m),
      error: (err) => this.error.set(err?.message ?? 'Unknown milestone error'),
    });

    this.api.listTenants().subscribe({
      next: (tenants) => this.tenants.set(tenants),
      error: (err) => this.error.set(err?.message ?? 'Unknown tenant error'),
    });

    this.api.framework().subscribe({
      next: (framework) => this.framework.set(framework),
      error: (err) => this.error.set(err?.message ?? 'Unknown framework error'),
    });
  }
}
