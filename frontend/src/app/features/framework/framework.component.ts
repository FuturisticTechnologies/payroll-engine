import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';

import { ApiService, PayrollFramework, Tenant } from '../../core/services/api.service';

@Component({
  selector: 'pf-framework',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="pf-page">
      <header class="pf-page__header">
        <div>
          <h1>Payroll framework</h1>
          <p class="pf-muted">Milestone 2 setup for employers, access and pay structure.</p>
        </div>
      </header>

      @if (error()) {
        <div class="pf-panel pf-panel--error">
          <strong>Framework unavailable</strong>
          <p>{{ error() }}</p>
        </div>
      } @else if (!framework()) {
        <p class="pf-muted">Loading...</p>
      } @else {
        @if (tenants().length > 0) {
          <div class="pf-panel">
            <h2>Employer tenants</h2>
            <div class="pf-tenant-grid">
              @for (tenant of tenants(); track tenant.id) {
                <article class="pf-tenant">
                  <span class="pf-status">{{ tenant.status }}</span>
                  <strong>{{ tenant.name }}</strong>
                  <small>{{ tenant.slug }}</small>
                  <dl>
                    <dt>PAYE</dt>
                    <dd>{{ tenant.paye_reference ?? 'Pending' }}</dd>
                    <dt>Accounts office</dt>
                    <dd>{{ tenant.accounts_office_reference ?? 'Pending' }}</dd>
                    <dt>Frequency</dt>
                    <dd>{{ tenant.default_pay_frequency }}</dd>
                  </dl>
                </article>
              }
            </div>
          </div>
        }

        <div class="pf-framework-grid">
          <article class="pf-panel">
            <h2>Pay frequencies</h2>
            <table class="pf-table">
              <thead>
                <tr>
                  <th>Frequency</th>
                  <th>Periods</th>
                  <th>HMRC</th>
                </tr>
              </thead>
              <tbody>
                @for (frequency of framework()!.pay_frequencies; track frequency.code) {
                  <tr>
                    <td>{{ frequency.label }}</td>
                    <td>{{ frequency.periods_per_tax_year }}</td>
                    <td><code>{{ frequency.hmrc_payment_frequency }}</code></td>
                  </tr>
                }
              </tbody>
            </table>
          </article>

          <article class="pf-panel">
            <h2>RBAC roles</h2>
            <div class="pf-list">
              @for (role of framework()!.roles; track role.code) {
                <div class="pf-list__item">
                  <strong>{{ role.name }}</strong>
                  <small>{{ role.description }}</small>
                </div>
              }
            </div>
          </article>

          <article class="pf-panel">
            <h2>Contract types</h2>
            <div class="pf-chip-row">
              @for (type of framework()!.contract_types; track type.code) {
                <span class="pf-chip">{{ type.label }}</span>
              }
            </div>
          </article>

          <article class="pf-panel">
            <h2>NI categories</h2>
            <div class="pf-chip-row">
              @for (category of framework()!.ni_categories; track category.code) {
                <span class="pf-chip"><strong>{{ category.code }}</strong>{{ category.label }}</span>
              }
            </div>
          </article>
        </div>
      }
    </section>
  `,
  styles: [
    `
      .pf-page {
        max-width: 1180px;
      }

      .pf-page__header {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: flex-start;
      }

      h1 {
        margin: 0 0 4px;
      }

      h2 {
        margin: 0 0 14px;
        font-size: 15px;
      }

      .pf-muted {
        color: var(--pf-color-ink-muted);
        margin: 0;
      }

      .pf-panel {
        margin-top: 22px;
        background: var(--pf-color-surface);
        border: 1px solid var(--pf-color-border);
        border-radius: var(--pf-radius);
        padding: 18px 20px;
        box-shadow: var(--pf-shadow);
      }

      .pf-panel--error {
        border-left: 4px solid var(--pf-color-danger);
        color: var(--pf-color-danger);
      }

      .pf-framework-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 16px;
      }

      .pf-tenant-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 14px;
      }

      .pf-tenant {
        position: relative;
        border: 1px solid var(--pf-color-border);
        border-radius: var(--pf-radius);
        padding: 16px;

        strong,
        small {
          display: block;
        }

        small {
          color: var(--pf-color-ink-muted);
          margin-top: 2px;
        }

        dl {
          display: grid;
          grid-template-columns: 110px 1fr;
          gap: 6px 10px;
          margin: 14px 0 0;
          font-size: 13px;
        }

        dt {
          color: var(--pf-color-ink-muted);
        }

        dd {
          margin: 0;
        }
      }

      .pf-status {
        position: absolute;
        right: 12px;
        top: 12px;
        border: 1px solid rgba(23, 184, 144, 0.35);
        border-radius: 999px;
        color: #08745f;
        font-size: 11px;
        padding: 3px 8px;
        text-transform: uppercase;
      }

      .pf-table {
        width: 100%;
        border-collapse: collapse;

        th,
        td {
          padding: 10px 8px;
          border-bottom: 1px solid var(--pf-color-border);
          text-align: left;
          font-size: 13px;
        }

        th {
          color: var(--pf-color-ink-muted);
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        tbody tr:last-child td {
          border-bottom: 0;
        }
      }

      .pf-list {
        display: grid;
        gap: 10px;
      }

      .pf-list__item {
        border-bottom: 1px solid var(--pf-color-border);
        padding-bottom: 10px;

        strong,
        small {
          display: block;
        }

        small {
          color: var(--pf-color-ink-muted);
          margin-top: 3px;
        }

        &:last-child {
          border-bottom: 0;
          padding-bottom: 0;
        }
      }

      .pf-chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .pf-chip {
        display: inline-flex;
        gap: 6px;
        align-items: center;
        border: 1px solid var(--pf-color-border);
        border-radius: 999px;
        padding: 6px 10px;
        font-size: 13px;
        background: #f8fafc;
      }

      @media (max-width: 900px) {
        .pf-framework-grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class FrameworkComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly tenants = signal<Tenant[]>([]);
  readonly framework = signal<PayrollFramework | null>(null);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
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
