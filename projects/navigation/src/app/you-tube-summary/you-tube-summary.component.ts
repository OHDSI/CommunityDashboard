import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { RouterModule } from '@angular/router';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';

@Component({
  selector: 'app-you-tube-summary',
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
  templateUrl: './you-tube-summary.component.html',
  styleUrls: [
    './you-tube-summary.component.css',
    '../dashboard/dashboard-summary.css',
  ]
})
export class YouTubeSummaryComponent {

  @Input() orientation: 'horizontal' | 'vertical' = 'vertical'

}
