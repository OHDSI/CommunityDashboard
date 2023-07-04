import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Input } from '@angular/core';
import { Project } from '../../project.service';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card'; 

@Component({
  selector: 'lib-project-card',
  standalone: true,
  imports: [
    MatCardModule,
    RouterModule,
    CommonModule
  ],
  templateUrl: './project-card.component.html',
  styleUrls: ['./project-card.component.css']
})
export class ProjectCardComponent {

  @Input({required: true}) project!: Project
}
