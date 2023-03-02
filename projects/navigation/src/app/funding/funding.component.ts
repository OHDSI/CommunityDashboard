import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FundingTableComponent } from './funding-table/funding-table.component';

@Component({
  selector: 'lib-funding',
  standalone: true,
  imports: [
    FundingTableComponent,
    CommonModule
  ],
  templateUrl: './funding.component.html',
  styleUrls: ['./funding.component.css']
})
export class FundingComponent {

}
