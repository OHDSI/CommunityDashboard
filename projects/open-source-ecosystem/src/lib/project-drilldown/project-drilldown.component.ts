import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CrumbComponent } from './crumb/crumb.component';

@Component({
  selector: 'lib-project-drilldown',
  standalone: true,
  imports: [
    CrumbComponent,
    CommonModule
  ],
  templateUrl: './project-drilldown.component.html',
  styleUrls: ['./project-drilldown.component.css']
})
export class ProjectDrilldownComponent {

}
