import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FundingTableComponent } from './funding-table/funding-table.component';
import { MatTabsModule } from '@angular/material/tabs';
import { CfpTableComponent } from './cfp-table/cfp-table.component';

@Component({
  selector: 'lib-funding',
  standalone: true,
  imports: [
    FundingTableComponent,
    CfpTableComponent,
    MatTabsModule,
    CommonModule
  ],
  templateUrl: './funding.component.html',
  styleUrls: ['./funding.component.css']
})
export class FundingComponent {

}
