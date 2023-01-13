import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { RouterModule } from '@angular/router';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';

@Component({
  selector: 'app-ehden-summary',
  standalone: true,
  imports: [
    IframePlotComponent,
    MatCardModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    RouterModule,
    CommonModule
  ],
  templateUrl: './ehden-summary.component.html',
  styleUrls: [
    './ehden-summary.component.css',
    '../dashboard/dashboard-summary.css',
  ]
})
export class EhdenSummaryComponent {

  @Input() orientation: 'horizontal' | 'vertical' = 'vertical'
  
}
