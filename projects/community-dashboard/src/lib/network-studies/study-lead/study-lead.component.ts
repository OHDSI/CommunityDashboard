import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';


@Component({
  selector: 'lib-study-lead',
  standalone: true,
  imports: [
    MatIconModule,
    MatCardModule,
    CommonModule
  ],
  templateUrl: './study-lead.component.html',
  styleUrls: ['./study-lead.component.css']
})
export class StudyLeadComponent {

  @Input({required: true}) lead!: string

  elevateClass = false

  elevate() {
    this.elevateClass = true
  }

  noelevate() {
    this.elevateClass = false
  }
}
