import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';

import { ApiService, Employee } from '../../core/services/api.service';

@Component({
  selector: 'pf-employees',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="pf-page">
      <header>
        <h1>Employees</h1>
        <p class="pf-muted">
          Milestone 2 employee structure with tenant scope, employee number and NI category.
        </p>
      </header>

      @if (loading()) {
        <p class="pf-muted">Loading...</p>
      } @else if (error()) {
        <p class="pf-error">Could not load employees: {{ error() }}</p>
      } @else if (employees().length === 0) {
        <div class="pf-empty">
          <p>No employees yet.</p>
          <p class="pf-muted">
            Use <code>POST /api/v1/employees</code> to create one. See OpenAPI docs at
            <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noopener">/docs</a>.
          </p>
        </div>
      } @else {
        <div class="pf-table-wrap">
          <table class="pf-table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Email</th>
                <th>Employee no.</th>
                <th>NI</th>
                <th>Tax</th>
                <th>Status</th>
                <th>Start date</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              @for (e of employees(); track e.id) {
                <tr>
                  <td>{{ e.first_name }} {{ e.last_name }}</td>
                  <td>{{ e.email }}</td>
                  <td><code>{{ e.employee_number }}</code></td>
                  <td><code>{{ e.national_insurance_number }} / {{ e.ni_category }}</code></td>
                  <td><code>{{ e.tax_code }}</code></td>
                  <td>{{ e.employment_status }}</td>
                  <td>{{ e.employment_start_date }}</td>
                  <td>{{ e.job_title ?? '-' }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </section>
  `,
  styles: [
    `
      .pf-page {
        max-width: 1180px;
      }

      h1 {
        margin: 0 0 4px;
      }

      .pf-muted {
        color: var(--pf-color-ink-muted);
        margin: 0;
      }

      .pf-error {
        color: var(--pf-color-danger);
      }

      .pf-empty {
        margin-top: 24px;
        padding: 24px;
        background: var(--pf-color-surface);
        border: 1px dashed var(--pf-color-border);
        border-radius: var(--pf-radius);
      }

      .pf-table-wrap {
        margin-top: 24px;
        overflow-x: auto;
        background: var(--pf-color-surface);
        box-shadow: var(--pf-shadow);
        border-radius: var(--pf-radius);
      }

      .pf-table {
        min-width: 920px;
        width: 100%;
        border-collapse: collapse;

        th,
        td {
          padding: 12px 14px;
          text-align: left;
          border-bottom: 1px solid var(--pf-color-border);
          font-size: 14px;
          white-space: nowrap;
        }

        th {
          background: #f1f5f9;
          font-weight: 600;
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: var(--pf-color-ink-muted);
        }

        tbody tr:last-child td {
          border-bottom: none;
        }
      }
    `,
  ],
})
export class EmployeesComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly employees = signal<Employee[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.api.listEmployees().subscribe({
      next: (list) => {
        this.employees.set(list);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(err?.message ?? 'Unknown error');
        this.loading.set(false);
      },
    });
  }
}
