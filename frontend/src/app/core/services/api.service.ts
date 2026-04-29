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
  first_name: string;
  last_name: string;
  email: string;
  national_insurance_number: string;
  tax_code: string;
  employment_start_date: string;
  job_title: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Thin wrapper around HttpClient for the backend API.
 *
 * Milestone 1 provides the smoke-testable calls (health, milestone info,
 * employee list). Real feature modules will own their own state via signals
 * or stores in later milestones.
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
}
