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
  templateUrl: './ehden-welcome.component.html',
  styleUrls: ['./ehden-welcome.component.scss']
})
export class EhdenWelcomeComponent {

}
