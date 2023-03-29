import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, Input, OnDestroy, ViewChild } from '@angular/core';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { TableDataSource } from '@community-dashboard/rest';
import { Publication, PubmedServiceSearchable } from '../publications/pubmed.service';

@Component({
  selector: 'app-pub-med-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
    FormsModule,
    CommonModule
  ],
  templateUrl: './pub-med-table.component.html',
  styleUrls: ['./pub-med-table.component.css']
})
export class PubMedTableComponent implements AfterViewInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<Publication>;
  dataSource: TableDataSource<Publication>;

  count = this.pubmedService.count()
  searchControl = new FormControl('')

  @Input()
  displayedColumns!: string[]

  constructor(
    private pubmedService: PubmedServiceSearchable,
  ) {
    this.dataSource = new TableDataSource(pubmedService);
  }

  ngAfterViewInit(): void {
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }

  searchSub = this.searchControl.valueChanges.subscribe(
    (v => {
      this.pubmedService.search.next(v ?? '')
    })
  )

  ngOnDestroy(): void {
    this.searchSub.unsubscribe()
  }

  formatAuthors(fullAuthorEdited: string) {
    return fullAuthorEdited.slice(1, fullAuthorEdited.length - 2).split("' '").join(', ')
  }
}
