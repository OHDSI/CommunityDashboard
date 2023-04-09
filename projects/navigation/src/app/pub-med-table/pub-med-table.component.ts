import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, ErrorHandler, Inject, Input, OnDestroy, ViewChild } from '@angular/core';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { AuthService, TableDataSource } from '@community-dashboard/rest';
import { Publication, PubmedService, PubmedServiceSearchable } from '../publications/pubmed.service';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import {MatDialog, MatDialogModule, MatDialogRef} from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { PublicationsManualService } from '../publications/publications-manual.service';
import { PublicationExceptionService } from '../publications/publication-exception.service';

@Component({
  selector: 'app-pub-med-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    MatDialogModule,
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

  count = this.pubmedServiceSearchable.count()
  searchControl = new FormControl('')
  user = this.authService.user

  s = this.authService.user.subscribe({
    next: u => {console.log('next', u)},
    error: r => {console.log('error', r)},
    complete: () => {console.log('complete')}
  })

  @Input()
  displayedColumns!: string[]

  constructor(
    private pubmedServiceSearchable: PubmedServiceSearchable,
    private publicationsManualService: PublicationsManualService,
    private publicationExceptionService: PublicationExceptionService,
    private errorHandler: ErrorHandler,
    @Inject('AuthToken') private authService: AuthService,
    private dialog: MatDialog,
  ) {
    this.dataSource = new TableDataSource(pubmedServiceSearchable);
  }

  ngAfterViewInit(): void {
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }

  searchSub = this.searchControl.valueChanges.subscribe(
    (v => {
      this.pubmedServiceSearchable.search.next(v ?? '')
    })
  )

  ngOnDestroy(): void {
    this.searchSub.unsubscribe()
  }

  formatAuthors(fullAuthorEdited: string) {
    return fullAuthorEdited
  }

  addPublicationDialog() {
    const dialogRef = this.dialog.open(NewPublicationDialog);
  }

  deletePublication(row: any) {
    if ('manualPublicationId' in row) {
      this.publicationsManualService.deleteById({id: row['manualPublicationId']}).subscribe()
    } else if ('pubmedID' in row) {
      if (row.exception) {
        this.publicationExceptionService.deleteById({id: row.exception}).subscribe()
      } else {
        this.publicationExceptionService.create({doc: {pubmedID: row['pubmedID']}}).subscribe()
      }
    } else {
      this.errorHandler.handleError(`Expected for to be pubmed or manual ${row}`)
    }
    
  }
}

@Component({
  selector: 'app-new-publication-dialog',
  templateUrl: './new-publication-dialog.component.html',
  styleUrls: ['./new-publication-dialog.component.css'],
  standalone: true,
  imports: [
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatProgressSpinnerModule,
    ReactiveFormsModule,
    FormsModule,
    CommonModule
  ],
})
export class NewPublicationDialog {

  constructor(
    private dialogRef: MatDialogRef<NewPublicationDialog>,
    private publicationsManualService: PublicationsManualService,
    private errorHandler: ErrorHandler,
  ) {}

  creationDateControl = new FormControl('', [Validators.required])
  authorsControl = new FormControl('', [Validators.required])
  titleControl = new FormControl('', [Validators.required])
  journalControl = new FormControl('', [Validators.required])
  snomedTermsControl = new FormControl('', [Validators.required])
  numCitationsControl = new FormControl<number|null>(null, [Validators.required])
  form = new FormGroup({
    creationDateControl: this.creationDateControl,
    authorsControl: this.authorsControl,
    titleControl: this.titleControl,
    journalControl: this.journalControl,
    snomedTermsControl: this.snomedTermsControl,
    numCitationsControl: this.numCitationsControl,
  })
  inProgress = false

  addPublication() {
    this.inProgress = true
    this.publicationsManualService.create({
      doc: {
        creationDate: this.creationDateControl.value!,
        fullAuthorEdited: this.authorsControl.value!,
        title: this.titleControl.value!,
        journalTitle: this.journalControl.value!,
        termFreq: this.snomedTermsControl.value!,
        numCitations: this.numCitationsControl.value!,
      }
    }).subscribe({
      next: _ => {
        this.inProgress = false
        this.dialogRef.close()
      },
      error: r => {
        this.errorHandler.handleError(`failed to create new publication ${r}`)
      }
    })
  }

}
