import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';

export interface HealthStatus {
  status: string;
  version: string;
  environment: string;
}

export interface MilestoneInfo {
  milestone: string;
  title: string;
  period: string;
  status: string;
}

export interface Employee {
  id: string;
  tenant_id: string;
  employee_number: string;
  first_name: string;
  last_name: string;
  email: string;
  national_insurance_number: string;
  tax_code: string;
  ni_category: string;
  employment_start_date: string;
  employment_status: string;
  job_title: string | null;
  created_at: string;
  updated_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  legal_name: string;
  slug: string;
  company_registration_number: string | null;
  paye_reference: string | null;
  accounts_office_reference: string | null;
  default_pay_frequency: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface PayFrequency {
  code: string;
  label: string;
  periods_per_tax_year: number;
  hmrc_payment_frequency: string;
}

export interface CatalogItem {
  code: string;
  label: string;
}

export interface RoleCatalogItem {
  code: string;
  name: string;
  description: string;
}

export interface PermissionCatalogItem {
  code: string;
  description: string;
}

export interface PayrollFramework {
  pay_frequencies: PayFrequency[];
  contract_types: CatalogItem[];
  ni_categories: CatalogItem[];
  roles: RoleCatalogItem[];
  permissions: PermissionCatalogItem[];
}

export interface PayrollAdjustment {
  employee_id: string;
  item_type: 'earning' | 'deduction';
  code: string;
  description: string;
  amount: string;
  taxable?: boolean;
  pensionable?: boolean;
}

export interface PayRunCreate {
  tax_year: number;
  period_number: number;
  pay_frequency: string;
  period_start: string;
  period_end: string;
  payment_date: string;
  employee_ids?: string[];
  adjustments?: PayrollAdjustment[];
}

export interface PayPeriod {
  id: string;
  tenant_id: string;
  tax_year: number;
  period_number: number;
  pay_frequency: string;
  period_start: string;
  period_end: string;
  payment_date: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface PayrollLineItem {
  id: string;
  item_type: string;
  code: string;
  description: string;
  amount: string;
  taxable: boolean;
  pensionable: boolean;
  source: string;
}

export interface PayRunLine {
  id: string;
  employee_id: string;
  contract_id: string;
  employee_number: string;
  employee_name: string;
  base_salary: string;
  additional_earnings: string;
  gross_pay: string;
  total_deductions: string;
  net_pay: string;
  currency: string;
  items: PayrollLineItem[];
}

export interface PayrollLedgerEntry {
  id: string;
  pay_run_id: string;
  sequence_number: number;
  entry_type: string;
  payload_hash: string;
  previous_hash: string | null;
  entry_hash: string;
  created_at: string;
}

export interface PayRunSummary {
  id: string;
  tenant_id: string;
  pay_period_id: string;
  status: string;
  employee_count: number;
  gross_earnings: string;
  total_deductions: string;
  net_pay: string;
  currency: string;
  calculation_version: string;
  calculated_at: string;
  ledger_entry_hash: string | null;
  created_at: string;
  updated_at: string;
}

export interface PayRun extends PayRunSummary {
  pay_period: PayPeriod;
  lines: PayRunLine[];
  ledger_entries: PayrollLedgerEntry[];
}

/**
 * Thin wrapper around HttpClient for the backend API.
 *
 * Feature modules keep state locally for now; the service gives the Angular
 * shell a typed contract over the FastAPI BFF surface.
 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  health(): Observable<HealthStatus> {
    return this.http.get<HealthStatus>(`${this.base}/health`);
  }

  milestone(): Observable<MilestoneInfo> {
    return this.http.get<MilestoneInfo>(`${this.base}/meta/milestone`);
  }

  listEmployees(): Observable<Employee[]> {
    return this.http.get<Employee[]>(`${this.base}/employees`);
  }

  listTenants(): Observable<Tenant[]> {
    return this.http.get<Tenant[]>(`${this.base}/tenants`);
  }

  framework(): Observable<PayrollFramework> {
    return this.http.get<PayrollFramework>(`${this.base}/framework`);
  }

  listPayRuns(): Observable<PayRunSummary[]> {
    return this.http.get<PayRunSummary[]>(`${this.base}/pay-runs`);
  }

  getPayRun(id: string): Observable<PayRun> {
    return this.http.get<PayRun>(`${this.base}/pay-runs/${id}`);
  }

  createPayRun(payload: PayRunCreate, idempotencyKey: string): Observable<PayRun> {
    return this.http.post<PayRun>(`${this.base}/pay-runs`, payload, {
      headers: { 'Idempotency-Key': idempotencyKey },
    });
  }
}
