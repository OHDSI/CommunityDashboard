import { Component } from '@angular/core';
import { PublicationGraphComponent } from './publication-graph/publication-graph.component';
import { MatButtonModule } from '@angular/material/button'; 
import { MatIconModule } from '@angular/material/icon'; 
import { CommonModule } from '@angular/common';

@Component({
  selector: 'lib-landing',
  standalone: true,
  templateUrl: 'landing.component.html',
  styleUrls: [
    'landing.component.css'
  ],
  imports: [
    PublicationGraphComponent,
    MatButtonModule,
    MatIconModule,
    CommonModule,
  ]
})
export class LandingComponent {

}
