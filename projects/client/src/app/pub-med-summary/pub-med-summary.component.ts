import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { RouterModule } from '@angular/router';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';

@Component({
  selector: 'app-pub-med-summary',
  standalone: true,
  imports: [
    IframePlotComponent,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatListModule,
    RouterModule,
    CommonModule
  ],
  templateUrl: './pub-med-summary.component.html',
  styleUrls: [
    './pub-med-summary.component.css',
    '../dashboard/dashboard-summary.css'
  ]
})
export class PubMedSummaryComponent {

  @Input() orientation: 'horizontal' | 'vertical' = 'vertical'
  
}
