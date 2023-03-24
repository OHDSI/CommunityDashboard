import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'app-phenotype-explorer-metrics-component',
  standalone: true,
  imports: [
    MatCardModule,
    CommonModule
  ],
  templateUrl: './phenotype-explorer-metrics.component.html',
  styleUrls: ['./phenotype-explorer-metrics.component.css']
})
export class PhenotypeExplorerMetricsComponent {

}
