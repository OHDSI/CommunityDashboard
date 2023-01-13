import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'app-pub-med-welcome',
  standalone: true,
  imports: [
    MatCardModule,
    CommonModule
  ],
  templateUrl: './pub-med-welcome.component.html',
  styleUrls: ['./pub-med-welcome.component.scss']
})
export class PubMedWelcomeComponent {

}
