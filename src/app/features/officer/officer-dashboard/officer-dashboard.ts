import { Component, inject, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';
import { LoanService } from '../../../core/services/loan.service';

@Component({
  selector: 'app-officer-dashboard',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, RouterModule],
  templateUrl: './officer-dashboard.html',
  styleUrl: './officer-dashboard.scss'
})
export class OfficerDashboard implements OnInit {
  private _loanService = inject(LoanService);
  private _cdr = inject(ChangeDetectorRef);

  officerBank: string = 'Bank';
  officerName: string = 'Officer';
  applications: any[] = [];
  loading = true;

  stats = {
    total: 0,
    approved: 0,
    pending: 0,
    highRisk: 0,
    approvalRate: 0
  };

  constructor() {
    this.officerBank = localStorage.getItem('officerBank') || 'Bank';
    this.officerName = localStorage.getItem('officerName') || 'Officer';
  }

  ngOnInit() {
    this.loadApplications();
  }

  loadApplications() {
    this.loading = true;
    console.log('Loading applications for:', this.officerBank);

    this._loanService.getApplications(this.officerBank).subscribe({
      next: (apps) => {
        console.log('Received applications:', apps);

        const total = apps.length;
        const approved = apps.filter(a => a.status === 'Approved').length;
        const pending = apps.filter(a => a.status === 'applied' || a.status === 'Pending').length;
        const approvalRate = total > 0 ? Math.round((approved / total) * 100) : 0;

        this.applications = apps.map(app => {
          let risk = 'Pending Analysis';
          const bankName = this.officerBank;

          if (app.prediction && app.prediction.bank_list) {
            const bankData = app.prediction.bank_list.find((b: any) => b.name === bankName);
            if (bankData && bankData.risk) {
              risk = bankData.risk;
            } else if (app.prediction.risk) {
              risk = app.prediction.risk;
            }
          }

          return {
            id: app._id,
            name: app.input?.Name || 'Applicant ' + app._id.substr(-4),
            income: app.input?.ApplicantIncome || 0,
            loanAmount: app.input?.LoanAmount || 0,
            risk: risk,
            status: app.status || 'Pending'
          };
        });

        const highRisk = this.applications.filter(a => a.risk === 'High').length;

        // Update stats with new object trigger change detection
        this.stats = {
          total,
          approved,
          pending,
          highRisk,
          approvalRate
        };

        this.loading = false;
        this._cdr.detectChanges();
      },
      error: (err) => {
        console.error('Failed to load applications', err);
        this.loading = false;
        this._cdr.detectChanges();
      }
    });
  }

  getStatusColor(status: string) {
    if (status === 'Approved') return 'text-green-600 bg-green-100 border-green-200';
    if (status === 'Rejected') return 'text-red-600 bg-red-100 border-red-200';
    if (status === 'Pending' || status === 'applied') return 'text-orange-600 bg-orange-100 border-orange-200';
    return 'text-blue-600 bg-blue-100 border-blue-200';
  }
}
