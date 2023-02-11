import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { StudySumariesService } from '../study-sumaries.service';

@Component({
  selector: 'app-study-explorer-metrics',
  standalone: true,
  imports: [
    MatCardModule,
    MatListModule,
    CommonModule
  ],
  templateUrl: './study-explorer-metrics.component.html',
  styleUrls: ['./study-explorer-metrics.component.css']
})
export class StudyExplorerMetricsComponent {

  completionMetrics = this.studySumariesService.find()

  constructor(
    private studySumariesService: StudySumariesService
  ) {}
  
}
