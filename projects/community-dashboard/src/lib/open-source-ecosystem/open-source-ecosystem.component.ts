import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { VisualizationTabsComponent } from './visualization-tabs/visualization-tabs.component';
import { ProjectListComponent } from './project-list/project-list.component';

@Component({
  selector: 'lib-open-source-ecosystem',
  standalone: true,
  templateUrl: './open-source-ecosystem.component.html',
  styleUrls: ['./open-source-ecosystem.component.css'],
  imports: [
    VisualizationTabsComponent,
    ProjectListComponent,
    CommonModule
  ]
})
export class OpenSourceEcosystemComponent {

}
