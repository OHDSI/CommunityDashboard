import { AfterViewInit, Component, Input, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTable, MatTableModule } from '@angular/material/table';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { Id, TableDataSource } from '@community-dashboard/rest';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { animate, state, style, transition, trigger } from '@angular/animations';
import { CfpOpsService, CfpOp } from '../cfp-ops.service';

@Component({
  selector: 'app-cfp-table',
  standalone: true,
  imports: [
    MatInputModule,
    MatFormFieldModule,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    FormsModule,
    ReactiveFormsModule,
    CommonModule
  ],
  templateUrl: './cfp-table.component.html',
  styleUrls: ['./cfp-table.component.css'],
  animations: [
    trigger('detailExpand', [
      state('collapsed', style({height: '0px', minHeight: '0'})),
      state('expanded', style({height: '*'})),
      transition('expanded <=> collapsed', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ],
})
export class CfpTableComponent implements AfterViewInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<CfpOp>;

  @Input() stage!: string

  dataSource!: TableDataSource<CfpOp>
  count = this.cfpOpsService.count()

  @Input()
  displayedColumns: string[] = [
    "DATE ADDED",
    // "OPPORTUNITY LINK",
    "JOURNAL",
    "THEME",
    "SUBMISSION DEADLINE",
  ]
  columnsToDisplayWithExpand = ['expand', ...this.displayedColumns]
  expanded: {id: Id} | null = null

  constructor(
    private cfpOpsService: CfpOpsService,
  ) {}

  ngAfterViewInit(): void {
    this.dataSource = new TableDataSource(
      this.cfpOpsService
    )
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }

  ngOnDestroy(): void {
  }

  // search(d: StudyPromotion) {
  //   const search = this.studyProgressSearchControl.value
  //   if (!search) { return false }
  //   return d.tags.join(' ').toLowerCase().includes(search.toLowerCase()) ||
  //     d.repoName.toLowerCase().includes(search.toLowerCase()) ||
  //     d.useCases.join(' ').toLowerCase().includes(search.toLowerCase()) ||
  //     d.studyType.join(' ').toLowerCase().includes(search.toLowerCase())
  // }

  toggleRow(row: CfpOp) {
    if (this.expanded?.id === row.id) {
      this.expanded = null
    } else {
      this.expanded = {id: row.id}
    }
  }
}
