import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormArray, FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

import { ApiService, Employee, PayRun, PayRunCreate, PayRunSummary } from '../../core/services/api.service';

type AdjustmentForm = FormGroup<{
  employee_id: FormControl<string>;
  item_type: FormControl<'earning' | 'deduction'>;
  code: FormControl<string>;
  description: FormControl<string>;
  amount: FormControl<string>;
  taxable: FormControl<boolean>;
  pensionable: FormControl<boolean>;
}>;

@Component({
  selector: 'pf-pay-runs',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="pf-page">
      <header class="pf-page__header">
        <div>
          <h1>Payroll runs</h1>
          <p class="pf-muted">Milestone 3 earnings, deductions and ledger-backed pay runs.</p>
        </div>
      </header>

      <div class="pf-grid">
        <form class="pf-panel pf-form" [formGroup]="form" (ngSubmit)="createRun()">
          <h2>Create pay run</h2>
          <div class="pf-form__grid">
            <label>
              Tax year
              <input type="number" formControlName="tax_year" />
            </label>
            <label>
              Period
              <input type="number" formControlName="period_number" />
            </label>
            <label>
              Frequency
              <select formControlName="pay_frequency">
                <option value="monthly">Monthly</option>
                <option value="weekly">Weekly</option>
                <option value="fortnightly">Fortnightly</option>
                <option value="four_weekly">Four weekly</option>
              </select>
            </label>
            <label>
              Period start
              <input type="date" formControlName="period_start" />
            </label>
            <label>
              Period end
              <input type="date" formControlName="period_end" />
            </label>
            <label>
              Payment date
              <input type="date" formControlName="payment_date" />
            </label>
            <label class="pf-form__wide">
              Employee scope
              <select formControlName="employee_id">
                <option value="">All eligible employees</option>
                @for (employee of employees(); track employee.id) {
                  <option [value]="employee.id">
                    {{ employee.first_name }} {{ employee.last_name }} - {{ employee.employee_number }}
                  </option>
                }
              </select>
            </label>
          </div>

          <div class="pf-adjustments" formArrayName="adjustments">
            <div class="pf-section-title">
              <h3>Manual adjustments</h3>
              <button type="button" class="pf-secondary-button" (click)="addAdjustment()">
                Add adjustment
              </button>
            </div>

            @if (adjustments.controls.length === 0) {
              <p class="pf-muted">No manual adjustments added.</p>
            }

            @for (adjustment of adjustments.controls; track $index) {
              <div class="pf-adjustment-row" [formGroupName]="$index">
                <label>
                  Employee
                  <select formControlName="employee_id">
                    <option value="">Select employee</option>
                    @for (employee of employees(); track employee.id) {
                      <option [value]="employee.id">
                        {{ employee.first_name }} {{ employee.last_name }}
                      </option>
                    }
                  </select>
                </label>
                <label>
                  Type
                  <select formControlName="item_type">
                    <option value="earning">Earning</option>
                    <option value="deduction">Deduction</option>
                  </select>
                </label>
                <label>
                  Code
                  <input type="text" formControlName="code" placeholder="BONUS" />
                </label>
                <label>
                  Description
                  <input type="text" formControlName="description" placeholder="Monthly bonus" />
                </label>
                <label>
                  Amount
                  <input type="number" min="0.01" step="0.01" formControlName="amount" />
                </label>
                <div class="pf-adjustment-row__flags">
                  <label class="pf-check">
                    <input type="checkbox" formControlName="taxable" />
                    Taxable
                  </label>
                  <label class="pf-check">
                    <input type="checkbox" formControlName="pensionable" />
                    Pensionable
                  </label>
                </div>
                <button
                  type="button"
                  class="pf-secondary-button pf-secondary-button--danger"
                  (click)="removeAdjustment($index)"
                >
                  Remove
                </button>
              </div>
            }
          </div>

          @if (error()) {
            <p class="pf-error">{{ error() }}</p>
          }

          <button type="submit" [disabled]="form.invalid || saving()">
            {{ saving() ? 'Calculating...' : 'Calculate run' }}
          </button>
        </form>

        @if (selectedRun(); as run) {
          <article class="pf-panel pf-run">
            <h2>Run details</h2>
            <div class="pf-totals">
              <div>
                <span>Gross</span>
                <strong>{{ money(run.gross_earnings, run.currency) }}</strong>
              </div>
              <div>
                <span>Deductions</span>
                <strong>{{ money(run.total_deductions, run.currency) }}</strong>
              </div>
              <div>
                <span>Net pay</span>
                <strong>{{ money(run.net_pay, run.currency) }}</strong>
              </div>
            </div>

            <dl>
              <dt>Employees</dt>
              <dd>{{ run.employee_count }}</dd>
              <dt>Period</dt>
              <dd>{{ run.pay_period.pay_frequency }} #{{ run.pay_period.period_number }}</dd>
              <dt>Ledger hash</dt>
              <dd><code>{{ run.ledger_entry_hash }}</code></dd>
            </dl>
          </article>
        }
      </div>

      <article class="pf-panel">
        <h2>Run history</h2>
        @if (loading()) {
          <p class="pf-muted">Loading...</p>
        } @else if (payRuns().length === 0) {
          <p class="pf-muted">No payroll runs have been calculated yet.</p>
        } @else {
          <div class="pf-table-wrap">
            <table class="pf-table">
              <thead>
                <tr>
                  <th>Calculated</th>
                  <th>Status</th>
                  <th>Employees</th>
                  <th>Gross</th>
                  <th>Deductions</th>
                  <th>Net</th>
                  <th>Ledger</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                @for (run of payRuns(); track run.id) {
                  <tr>
                    <td>{{ run.calculated_at | date: 'medium' }}</td>
                    <td>{{ run.status }}</td>
                    <td>{{ run.employee_count }}</td>
                    <td>{{ money(run.gross_earnings, run.currency) }}</td>
                    <td>{{ money(run.total_deductions, run.currency) }}</td>
                    <td>{{ money(run.net_pay, run.currency) }}</td>
                    <td><code>{{ shortHash(run.ledger_entry_hash) }}</code></td>
                    <td>
                      <button
                        type="button"
                        class="pf-table-button"
                        [disabled]="loadingRunId() === run.id"
                        (click)="selectRun(run.id)"
                      >
                        {{ loadingRunId() === run.id ? 'Loading...' : 'Inspect' }}
                      </button>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </article>

      @if (selectedRun()?.lines?.length) {
        <article class="pf-panel">
          <h2>Employee results</h2>
          <div class="pf-table-wrap">
            <table class="pf-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Base</th>
                  <th>Extra</th>
                  <th>Deductions</th>
                  <th>Net</th>
                  <th>Line items</th>
                </tr>
              </thead>
              <tbody>
                @for (line of selectedRun()!.lines; track line.id) {
                  <tr>
                    <td>{{ line.employee_name }} <code>{{ line.employee_number }}</code></td>
                    <td>{{ money(line.base_salary, line.currency) }}</td>
                    <td>{{ money(line.additional_earnings, line.currency) }}</td>
                    <td>{{ money(line.total_deductions, line.currency) }}</td>
                    <td>{{ money(line.net_pay, line.currency) }}</td>
                    <td>
                      <div class="pf-line-items">
                        @for (item of line.items; track item.id) {
                          <span class="pf-line-item" [class.pf-line-item--deduction]="item.item_type === 'deduction'">
                            {{ item.code }} {{ money(item.amount, line.currency) }}
                          </span>
                        }
                      </div>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </article>
      }

      @if (selectedRun()?.ledger_entries?.length) {
        <article class="pf-panel">
          <h2>Ledger evidence</h2>
          <div class="pf-table-wrap">
            <table class="pf-table">
              <thead>
                <tr>
                  <th>Sequence</th>
                  <th>Entry type</th>
                  <th>Payload hash</th>
                  <th>Previous hash</th>
                  <th>Entry hash</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                @for (entry of selectedRun()!.ledger_entries; track entry.id) {
                  <tr>
                    <td>{{ entry.sequence_number }}</td>
                    <td>{{ entry.entry_type }}</td>
                    <td><code>{{ shortHash(entry.payload_hash) }}</code></td>
                    <td><code>{{ shortHash(entry.previous_hash) }}</code></td>
                    <td><code>{{ shortHash(entry.entry_hash) }}</code></td>
                    <td>{{ entry.created_at | date: 'medium' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </article>
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

      .pf-error {
        color: var(--pf-color-danger);
        margin: 0;
      }

      .pf-grid {
        display: grid;
        grid-template-columns: minmax(320px, 1fr) minmax(280px, 0.9fr);
        gap: 16px;
        margin-top: 22px;
      }

      .pf-panel {
        margin-top: 22px;
        background: var(--pf-color-surface);
        border: 1px solid var(--pf-color-border);
        border-radius: var(--pf-radius);
        padding: 18px 20px;
        box-shadow: var(--pf-shadow);
      }

      .pf-grid .pf-panel {
        margin-top: 0;
      }

      .pf-form {
        display: grid;
        gap: 14px;
      }

      .pf-form__grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
      }

      .pf-form__wide {
        grid-column: span 2;
      }

      .pf-section-title {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;

        h3 {
          margin: 0;
          font-size: 13px;
        }
      }

      .pf-adjustments {
        display: grid;
        gap: 10px;
        border-top: 1px solid var(--pf-color-border);
        padding-top: 14px;
      }

      .pf-adjustment-row {
        display: grid;
        grid-template-columns: 1.2fr 110px 120px minmax(160px, 1fr) 120px 170px auto;
        gap: 10px;
        align-items: end;
        border: 1px solid var(--pf-color-border);
        border-radius: var(--pf-radius);
        padding: 12px;
        background: #f8fafc;
      }

      .pf-adjustment-row__flags {
        display: flex;
        gap: 10px;
        align-items: center;
        padding-bottom: 9px;
      }

      .pf-check {
        display: inline-flex;
        grid-template-columns: none;
        gap: 6px;
        align-items: center;
        color: var(--pf-color-ink);
      }

      .pf-check input {
        width: auto;
      }

      label {
        display: grid;
        gap: 6px;
        font-size: 12px;
        color: var(--pf-color-ink-muted);
      }

      input,
      select {
        border: 1px solid var(--pf-color-border);
        border-radius: var(--pf-radius);
        padding: 9px 10px;
        font: inherit;
        color: var(--pf-color-ink);
        background: #fff;
      }

      button {
        width: fit-content;
        border: 0;
        border-radius: var(--pf-radius);
        background: var(--pf-color-primary);
        color: #fff;
        padding: 10px 14px;
        font-weight: 600;
        cursor: pointer;

        &:disabled {
          opacity: 0.6;
          cursor: default;
        }
      }

      .pf-secondary-button {
        border: 1px solid var(--pf-color-border);
        background: #fff;
        color: var(--pf-color-ink);
        padding: 8px 10px;
      }

      .pf-secondary-button--danger {
        color: var(--pf-color-danger);
      }

      .pf-table-button {
        border: 1px solid var(--pf-color-border);
        background: #fff;
        color: var(--pf-color-primary);
        padding: 6px 10px;
        font-size: 12px;

        &:disabled {
          color: var(--pf-color-ink-muted);
        }
      }

      .pf-totals {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin-bottom: 16px;

        div {
          border: 1px solid var(--pf-color-border);
          border-radius: var(--pf-radius);
          padding: 10px;
        }

        span,
        strong {
          display: block;
        }

        span {
          color: var(--pf-color-ink-muted);
          font-size: 11px;
          text-transform: uppercase;
        }
      }

      dl {
        display: grid;
        grid-template-columns: 90px 1fr;
        gap: 8px 12px;
        margin: 0;
        font-size: 13px;
      }

      dt {
        color: var(--pf-color-ink-muted);
      }

      dd {
        margin: 0;
        min-width: 0;
        overflow-wrap: anywhere;
      }

      .pf-table-wrap {
        overflow-x: auto;
      }

      .pf-table {
        min-width: 940px;
        width: 100%;
        border-collapse: collapse;

        th,
        td {
          padding: 11px 12px;
          text-align: left;
          border-bottom: 1px solid var(--pf-color-border);
          font-size: 13px;
          white-space: nowrap;
        }

        th {
          background: #f1f5f9;
          font-weight: 600;
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: var(--pf-color-ink-muted);
        }
      }

      .pf-line-items {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        min-width: 240px;
      }

      .pf-line-item {
        border: 1px solid rgba(8, 116, 95, 0.25);
        border-radius: 999px;
        background: #ecfdf5;
        color: #08745f;
        padding: 3px 8px;
        font-size: 11px;
      }

      .pf-line-item--deduction {
        border-color: rgba(185, 28, 28, 0.22);
        background: #fef2f2;
        color: #b91c1c;
      }

      @media (max-width: 980px) {
        .pf-grid,
        .pf-form__grid,
        .pf-adjustment-row {
          grid-template-columns: 1fr;
        }

        .pf-form__wide {
          grid-column: auto;
        }
      }
    `,
  ],
})
export class PayRunsComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly employees = signal<Employee[]>([]);
  readonly payRuns = signal<PayRunSummary[]>([]);
  readonly selectedRun = signal<PayRun | null>(null);
  readonly loading = signal(true);
  readonly loadingRunId = signal<string | null>(null);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly form = new FormGroup({
    tax_year: new FormControl(2026, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(2000), Validators.max(2100)],
    }),
    period_number: new FormControl(6, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(1), Validators.max(53)],
    }),
    pay_frequency: new FormControl('monthly', {
      nonNullable: true,
      validators: [Validators.required],
    }),
    period_start: new FormControl('2026-06-01', {
      nonNullable: true,
      validators: [Validators.required],
    }),
    period_end: new FormControl('2026-06-30', {
      nonNullable: true,
      validators: [Validators.required],
    }),
    payment_date: new FormControl('2026-06-30', {
      nonNullable: true,
      validators: [Validators.required],
    }),
    employee_id: new FormControl('', {
      nonNullable: true,
    }),
    adjustments: new FormArray<AdjustmentForm>([]),
  });

  ngOnInit(): void {
    this.loadRuns();
    this.loadEmployees();
  }

  get adjustments(): FormArray<AdjustmentForm> {
    return this.form.controls.adjustments;
  }

  addAdjustment(): void {
    this.adjustments.push(
      new FormGroup({
        employee_id: new FormControl('', {
          nonNullable: true,
          validators: [Validators.required],
        }),
        item_type: new FormControl<'earning' | 'deduction'>('earning', {
          nonNullable: true,
          validators: [Validators.required],
        }),
        code: new FormControl('', {
          nonNullable: true,
          validators: [Validators.required, Validators.maxLength(40)],
        }),
        description: new FormControl('', {
          nonNullable: true,
          validators: [Validators.required, Validators.maxLength(255)],
        }),
        amount: new FormControl('', {
          nonNullable: true,
          validators: [Validators.required, Validators.min(0.01)],
        }),
        taxable: new FormControl(true, { nonNullable: true }),
        pensionable: new FormControl(true, { nonNullable: true }),
      }),
    );
  }

  removeAdjustment(index: number): void {
    this.adjustments.removeAt(index);
  }

  createRun(): void {
    if (this.form.invalid) {
      return;
    }
    const raw = this.form.getRawValue();
    const adjustments = raw.adjustments.map((adjustment) => ({
      employee_id: adjustment.employee_id,
      item_type: adjustment.item_type,
      code: adjustment.code.trim(),
      description: adjustment.description.trim(),
      amount: Number(adjustment.amount).toFixed(2),
      taxable: adjustment.taxable,
      pensionable: adjustment.pensionable,
    }));
    const payload: PayRunCreate = {
      tax_year: raw.tax_year,
      period_number: raw.period_number,
      pay_frequency: raw.pay_frequency,
      period_start: raw.period_start,
      period_end: raw.period_end,
      payment_date: raw.payment_date,
      employee_ids: raw.employee_id ? [raw.employee_id] : undefined,
      adjustments: adjustments.length > 0 ? adjustments : undefined,
    };
    this.saving.set(true);
    this.error.set(null);
    this.api.createPayRun(payload, `ui-pay-run-${crypto.randomUUID()}`).subscribe({
      next: (run) => {
        this.selectedRun.set(run);
        this.saving.set(false);
        this.loadRuns();
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? err?.message ?? 'Could not calculate pay run');
        this.saving.set(false);
      },
    });
  }

  money(value: string, currency: string): string {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency,
    }).format(Number(value));
  }

  shortHash(value: string | null): string {
    return value ? `${value.slice(0, 10)}...` : '-';
  }

  selectRun(id: string): void {
    this.loadingRunId.set(id);
    this.error.set(null);
    this.api.getPayRun(id).subscribe({
      next: (run) => {
        this.selectedRun.set(run);
        this.loadingRunId.set(null);
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? err?.message ?? 'Could not load pay run evidence');
        this.loadingRunId.set(null);
      },
    });
  }

  private loadRuns(): void {
    this.loading.set(true);
    this.api.listPayRuns().subscribe({
      next: (runs) => {
        this.payRuns.set(runs);
        this.loading.set(false);
        if (!this.selectedRun() && runs.length > 0) {
          this.selectRun(runs[0].id);
        }
      },
      error: (err) => {
        this.error.set(err?.message ?? 'Could not load payroll runs');
        this.loading.set(false);
      },
    });
  }

  private loadEmployees(): void {
    this.api.listEmployees().subscribe({
      next: (employees) => this.employees.set(employees),
      error: (err) => this.error.set(err?.message ?? 'Could not load employees'),
    });
  }
}
